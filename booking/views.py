import uuid
from datetime import date
from django.contrib import messages
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from .models import Reservation
from .services import ROOMS, available_days, reserve_slot


@require_GET
def index(request):
    if "sandbox" not in request.session:
        request.session["sandbox"] = str(uuid.uuid4())
    days = available_days()
    try:
        selected_day = date.fromisoformat(request.GET.get("day", str(days[0])))
    except ValueError:
        selected_day = days[0]
    if selected_day not in days:
        selected_day = days[0]
    room = request.GET.get("room", "focus")
    if room not in ROOMS:
        room = "focus"
    reservations = list(
        Reservation.objects.filter(sandbox=request.session["sandbox"], day__gte=days[0])
    )
    occupied = {
        r.hour for r in reservations if r.day == selected_day and r.room == room
    }
    for reservation in reservations:
        reservation.room_name = ROOMS[reservation.room]["name"]
    slots = [{"hour": h, "end": h + 1, "taken": h in occupied} for h in range(9, 17)]
    return render(
        request,
        "index.html",
        {
            "days": days,
            "selected_day": selected_day,
            "rooms": ROOMS,
            "room": room,
            "selected_room": ROOMS[room],
            "slots": slots,
            "reservations": reservations,
            "free_count": 8 - len(occupied),
            "race_hour": next((s["hour"] for s in slots if not s["taken"]), None),
        },
    )


@require_POST
def reserve(request):
    wants_json = request.headers.get("Accept") == "application/json"
    if "sandbox" not in request.session:
        return JsonResponse({"error": "Open the booking page first."}, status=400)
    try:
        day = date.fromisoformat(request.POST.get("day", ""))
        hour = int(request.POST.get("hour", ""))
        room = request.POST.get("room", "")
        reservation = reserve_slot(request.session["sandbox"], room, day, hour)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid booking slot."}, status=400)
    if wants_json:
        return JsonResponse(
            {"status": "reserved" if reservation else "conflict"},
            status=201 if reservation else 409,
        )
    if reservation:
        messages.success(request, "Reserved. Your room is ready in this demo sandbox.")
    else:
        messages.warning(
            request, "That slot was just taken. No duplicate reservation was created."
        )
    return redirect(f"{reverse('index')}?room={room}&day={day}#booking-feedback")


@require_POST
def cancel(request, reference):
    if "sandbox" not in request.session:
        return HttpResponseBadRequest("Open the booking page first.")
    reservation = get_object_or_404(
        Reservation, reference=reference, sandbox=request.session["sandbox"]
    )
    room, day = reservation.room, reservation.day
    reservation.delete()
    messages.success(request, "Reservation cancelled. The slot is available again.")
    return redirect(f"{reverse('index')}?room={room}&day={day}#booking-feedback")


@require_GET
def health(request):
    Reservation.objects.exists()
    return JsonResponse({"status": "ok"})
