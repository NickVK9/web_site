import logging
from django.http import HttpResponse
from django.template import RequestContext
from django.template.loader import render_to_string

from page_content.models import HelpText
import simplejson as json
from dateutil import parser
from book_trip.models import TravelerProfile, Trip_Traveller_Seat
from book_trip import views #import get_current_booking_session
from book_trip import rexHelperFunctions #import *
from customer_dashboard.rexHelperFunctions import getRexTravellerProfileByKey
from customer_dashboard.models import UserProfile
from rexweb.core.errors import NotFoundException

logger = logging.getLogger(__name__)

def applyCoupon(request):
	json_data = {}
	bookSession = views.get_current_booking_session(request)

	couponIsValid = False
	message = ""

	if request.POST:
		couponCode = request.POST['couponCode']

		rexCrs = rexHelperFunctions.getRexClient()
		try:
			discount = rexCrs.fetch_discount(couponCode)
		except NotFoundException:
			discount = None
		except Exception as exc:
			logger.error(exc)
			discount = None

		if not discount:
			couponIsValid = False
			message = "Sorry, the coupon code entered appears to be invalid."
		else:
			couponIsValid = True
			bookSession.promo_code = couponCode

			try:
				rexHelperFunctions.priceOutBooking(bookSession)
			except Exception as exc:
				message = str(exc)
				couponIsValid = False
				bookSession.promo_code = ''
				rexHelperFunctions.priceOutBooking(bookSession)

			bookSession.save()

			context = {'bookSession': bookSession, }
			html = render_to_string('book_trip/amount_due_template.html', context,
			                        context_instance=RequestContext(request))
			json_data['costSummaryHtml'] = html

		json_data['isValid'] = couponIsValid
		json_data['message'] = message

		return HttpResponse(json.dumps(json_data), content_type='application/json')


def getCostSummary(request):
	json_data = {}
	bookSession = views.get_current_booking_session(request)

	context = {'bookSession': bookSession, }
	html = render_to_string('book_trip/amount_due_template.html', context, context_instance=RequestContext(request))
	json_data['html'] = html

	return HttpResponse(json.dumps(json_data), content_type='application/json')


def setOrigin(request):
	json_data = {}
	bookSession = views.get_current_booking_session(request)

	if request.POST:

		originId = request.POST['originId']
		bookSession.set_origin_rex_key(originId)
		bookSession.save()

		# Get destinations for this origin
		rexCrs = getRexClient()

		destinations = rexCrs.get_trip_destinations(originId)

		destDictionary = {}

		for token in destinations:
			destDictionary[token.key] = token.name

		json_data['destinations'] = destDictionary

		return HttpResponse(json.dumps(json_data), content_type='application/json')


def setDestination(request):
	json_data = {}
	bookSession = get_current_booking_session(request)

	if request.POST:
		destinationId = request.POST['destinationId']

		bookSession.set_destination_rex_key(destinationId)
		bookSession.save()

		return HttpResponse(json.dumps(json_data), content_type='application/json')


def setReturnOrigin(request):
	json_data = {}
	bookSession = get_current_booking_session(request)

	if request.POST:
		originId = request.POST['returnOriginId']

		bookSession.clear_trips_from_this_location(bookSession.destination_rex_key)
		bookSession.return_trip = None
		bookSession.save()

		# Get valid destinations for this point
		rexCrs = getRexClient()
		locations = rexCrs.get_trip_destinations(originId)

		locDict = buildDictionaryOfLocations(locations)

		json_data['destinations'] = locDict

		return HttpResponse(json.dumps(json_data), content_type='application/json')


def setDepartureDate(request):
	bookSession = get_current_booking_session(request)

	if request.POST:
		tripDate = parser.parse(request.POST['tripDate'])
		timeFrame = request.POST['timeFrame']

		bookSession.departure_date = tripDate
		bookSession.departure_time = timeFrame
		bookSession.save()

		return refreshOriginTrips(request)


def setReturnDate(request):
	bookSession = get_current_booking_session(request)

	if request.POST:
		tripDate = parser.parse(request.POST['tripDate'])
		timeFrame = request.POST['timeFrame']

		bookSession.return_date = tripDate
		bookSession.return_time = timeFrame
		bookSession.save()

		return refreshReturnTrips(request)


def getDestinations(request):
	json_data = {}

	if request.POST:
		originId = request.POST['originId']
		rexCrs = getRexClient()

		destinations = rexCrs.get_trip_destinations(originId)

		destDictionary = buildDictionaryOfLocations(destinations)

		json_data['destinations'] = destDictionary

		return HttpResponse(json.dumps(json_data), content_type='application/json')


def refreshOriginTrips(request):
	bookSession = get_current_booking_session(request)

	if request.POST:
		originId = request.POST['originId']
		destinationId = request.POST['destinationId']
		tripDateString = request.POST['tripDate']
		tripDate = parser.parse(tripDateString)
		timeFrame = request.POST['timeFrame']

		bookSession.origin_rex_key = originId
		bookSession.destination_rex_key = destinationId
		bookSession.departure_date = tripDate
		bookSession.departure_time = timeFrame

		buildTripsForBookingSession(bookSession, bookSession.origin_rex_key,
		                            bookSession.destination_rex_key,
		                            bookSession.departure_date.date(),
		                            bookSession.departure_time)

		return findTrips(request)


def refreshReturnTrips(request):
	bookSession = get_current_booking_session(request)

	if request.POST:
		originId = request.POST['originId']
		destinationId = request.POST['destinationId']
		tripDateString = request.POST['tripDate']
		tripDate = parser.parse(tripDateString)
		timeFrame = request.POST['timeFrame']

		buildTripsForBookingSession(bookSession, originId,
		                            destinationId,
		                            tripDate.date(),
		                            timeFrame)

		return findTrips(request)


def findTrips(request):
	json_data = {}
	bookSession = get_current_booking_session(request)
	autoSelectTrip = False
	tripId = None

	if request.POST:
		originId = request.POST['originId']
		destinationId = request.POST['destinationId']
		tripDateString = request.POST['tripDate']
		tripDate = parser.parse(tripDateString)
		timeFrame = request.POST['timeFrame']
		groupName = request.POST['groupName']

		trips = bookSession.trips.filter(origin_key=originId, parent=None).order_by('id', )
		if len(trips) == 1:
			autoSelectTrip = True
			autoSelectedTrip = trips[0]

			tripId = autoSelectedTrip.id
			trip = bookSession.trips.get(id=tripId)
			bookSession.trip_selected(trip)
			bookSession.save()

		context = {'bookSession': bookSession, 'trips': trips, 'groupName': groupName}
		html = render_to_string('book_trip/trip_list_template.html', context, context_instance=RequestContext(request))
		json_data['html'] = html
		json_data['autoSelectTrip'] = autoSelectTrip
		json_data['autoTripId'] = tripId

		if len(trips) < 1:
			json_data['trips_available'] = False
		else:
			json_data['trips_available'] = True

		return HttpResponse(json.dumps(json_data), content_type='application/json')


def refreshPrice(request):
	json_data = {}
	bookSession = get_current_booking_session(request)
	priceOutBooking(bookSession)
	bookSession.save()

	context = {'bookSession': bookSession, }
	html = render_to_string('book_trip/price_total_template.html', context, )

	json_data['html'] = html

	return HttpResponse(json.dumps(json_data), content_type='application/json')


def tripSelected(request):
	bookSession = get_current_booking_session(request)

	if request.POST:
		tripId = request.POST['tripId']
		trip = bookSession.trips.get(id=tripId)
		bookSession.trip_selected(trip)
		bookSession.save()

		return refreshPrice(request)


def checkForTripAlert(request):
	bookSession = get_current_booking_session(request)
	json_data = {}
	alert_msgs = []
	if request.POST:
		tripId = request.POST['tripId']
		trip = bookSession.trips.get(id=tripId)

		rexCrs = getRexClient()
		prodToken = RexToken(trip.product_key, trip.product_name)
		bookingAlerts = rexCrs.fetch_booking_alerts(prodToken)

		for alert in bookingAlerts:
			alert_msgs.append({'title': alert.title, 'body': alert.body, 'img_url': trip.alert_msg_img_url})

		json_data['alerts'] = alert_msgs
		return HttpResponse(json.dumps(json_data), content_type='application/json')


def getSeatingForTrip(request):
	bookSession = get_current_booking_session(request)
	json_data = {}

	if request.POST:

		tripId = request.POST['tripId']
		trip = bookSession.trips.get(id=tripId)
		rexCrs = getRexClient()

		try:
			seating = rexCrs.fetch_seating_model(trip.facility_key, tripDate=trip.depart_date)
			json_data['seatingNotAvail'] = False
		except Exception as exc:
			logging.error(exc)
			seating = None
			json_data['seatingNotAvail'] = True

		dict = {'tripId': trip.id, 'seats': []}

		if seating:
			dict['name'] = seating.name
			dict['description'] = seating.description

			for seat in seating.seats:
				seatDict = {}
				seatDict['number'] = seat.number
				seatDict['style'] = seat.style
				seatDict['description'] = seat.description
				seatDict['attributes'] = seat.attributes

				dict['seats'].append(seatDict)

		json_data['seating'] = dict

		assignments = trip.seat_assignments.filter(trip=trip)

		context = {'seat_assignments': assignments, }
		html = render_to_string('book_trip/passenger_seat_template.html', context,
		                        context_instance=RequestContext(request))
		json_data['passengerHtml'] = html

		return HttpResponse(json.dumps(json_data), content_type='application/json')


def getTravelerProfile(request):
	bookSession = get_current_booking_session(request)
	json_data = {}

	if request.POST:
		profileID = request.POST['profileID']

		profile = bookSession.traveler_profiles.get(id=profileID)

		dict = {}

		dict['traveler_class'] = profile.traveler_class
		dict['first_name'] = profile.first_name
		dict['last_name'] = profile.last_name
		dict['age'] = profile.age
		dict['phone'] = profile.phone
		dict['id'] = profile.id

		json_data['profile'] = dict

		return HttpResponse(json.dumps(json_data), content_type='application/json')


def saveTravelerProfile(request):
	bookSession = get_current_booking_session(request)
	json_data = {}

	if request.POST:

		#traveler_class = request.POST['travelerType']
		traveler_class = 'ADULT'
		first_name = request.POST['firstName']
		last_name = request.POST['lastName']
		#age = request.POST['age']
		phone = request.POST['phone']
		id = request.POST['id']

		profile = None

		if id != '0':
			try:
				profile = bookSession.traveler_profiles.get(id=id)
			except:
				profile = None

		if profile == None:
			profile = TravelerProfile(bookTripSession=bookSession)

		profile.traveler_class = traveler_class
		profile.first_name = first_name
		profile.last_name = last_name
		#profile.age = age
		profile.phone = phone
		profile.save()

		priceOutBooking(bookSession)
		bookSession.save()

		dict = {}

		json_data['profile'] = dict

		return HttpResponse(json.dumps(json_data), content_type='application/json')


def linkTravelerProfile(request):
	bookSession = get_current_booking_session(request)
	json_data = {}

	if request.POST:
		travellerId = request.POST['id']
		rexProfileId = request.POST['profileId']

		profile = bookSession.traveler_profiles.get(id=travellerId)

		userProfile = UserProfile.objects.get(user=request.user)
		rexProfile = getRexTravellerProfileByKey(userProfile.rex_customer_key, rexProfileId)

		profile.rex_key = rexProfileId
		profile.first_name = rexProfile.firstName
		profile.last_name = rexProfile.lastName
		profile.phone = rexProfile.phoneDay

		profile.save()

		json_data['firstName'] = profile.first_name
		json_data['lastName'] = profile.last_name
		json_data['phone'] = profile.phone

		return HttpResponse(json.dumps(json_data), content_type='application/json')


def getPassengerList(request):
	json_data = {}
	bookSession = get_current_booking_session(request)

	context = {'bookSession': bookSession, }
	html = render_to_string('book_trip/passenger_list_template.html', context, context_instance=RequestContext(request))
	json_data['html'] = html

	return HttpResponse(json.dumps(json_data), content_type='application/json')


def assignPassengerToSeat(request):
	json_data = {}
	bookSession = get_current_booking_session(request)

	if request.POST:
		tripId = request.POST['tripId']
		seatNo = request.POST['seatNo']
		passengerId = request.POST['passengerId']

		trip = bookSession.trips.get(id=tripId)

		# if we have another passenger assigned to this seat then remove it
		otherPassAssignments = Trip_Traveller_Seat.objects.filter(trip=trip, seat_no=seatNo)
		for traveller in otherPassAssignments:
			traveller.seat_no = 'None'
			traveller.save()

		# Now assign the seat to the latest passenger.
		travellers = Trip_Traveller_Seat.objects.filter(trip=trip, travelerProfile__id=passengerId)

		if len(travellers) < 1:
			return

		traveller_seat = travellers[0]
		traveller_seat.seat_no = seatNo
		traveller_seat.save()

		# return a fresh list of passenger / seat assignments
		context = {'seat_assignments': trip.seat_assignments.all, }
		html = render_to_string('book_trip/passenger_seat_template.html', context,
		                        context_instance=RequestContext(request))
		json_data['passengerHtml'] = html

		return HttpResponse(json.dumps(json_data), content_type='application/json')


def getHelpText(request):
	json_data = {}
	helpText = None

	if request.POST:
		resource_ID = request.POST['resourceID']

		if resource_ID == 'security':
			helpText = HelpText.objects.filter(resource_id='security')

			if len(helpText) < 2:
				helpText = HelpText.objects.filter(resource_id='security')[0]

		if resource_ID == 'terms':
			helpText = HelpText.objects.filter(resource_id='terms')

			if len(helpText) < 2:
				helpText = HelpText.objects.filter(resource_id='terms')[0]

		if resource_ID == 'privacy':
			helpText = HelpText.objects.filter(resource_id='privacy')

			if len(helpText) < 2:
				helpText = HelpText.objects.filter(resource_id='privacy')[0]

	context = {'helpText': helpText, }
	html = render_to_string('help_text.html', context, context_instance=RequestContext(request))
	json_data['html'] = html

	return HttpResponse(json.dumps(json_data), content_type='application/json')