from decimal import Decimal
import pickle
import logging
from django.conf import settings
from book_trip import models #import Trip
from rexweb.crs.order import CreditCard, CreditCardPayment
from rexweb.crs.trip import Trip as RexTrip
from rexweb.core.generic import Token as RexToken, Money as RexMoney
from rexweb.crm.traveler import Traveler as RexTraveler
from rexweb.core.errors import PaymentException, SalesException, NotFoundException
from book_trip.utility import getRexClient


def isCouponCodeValid(couponCode):
	rexCrs = getRexClient()

	coupons = rexCrs._fetch_all_coupon_issues()

	for coupon in coupons:
		if coupon.key == couponCode:
			return True

	return False


def payForBooking(bookSession, paymentForm, rexCustomer, payerInfo, messages):
	rexCrs = getRexClient()
	customer = None

	# Customer
	if rexCustomer == None:
		customer = rexCrs.fetch_anonymous_web_customer()
	else:
		customer = rexCustomer

	# Proposed bookings
	if bookSession.pickled_rex_booking_session and len(bookSession.pickled_rex_booking_session) > 1:
		bookings = pickle.loads(str(bookSession.pickled_rex_booking_session))

	else:
		bookings = getProposedBookings(bookSession, messages)

	if len(messages) > 0:
		return None

	if paymentForm:
		# Credit card payment
		expireDate = "%s/%s" % (paymentForm.cleaned_data['exp_month'], paymentForm.cleaned_data['exp_year'])

		nameOnCard = "%s %s" % (paymentForm.cleaned_data['first_name'], paymentForm.cleaned_data['last_name'])

		card = CreditCard(paymentForm.cleaned_data['card_number'],
		                  expireDate, paymentForm.cleaned_data['security_number'], nameOnCard)

		payment = CreditCardPayment(RexMoney(settings.DEFAULT_CURRENCY_CODE, bookSession.grand_total), card)

	else:
		payment = None

	try:
		salesOrder = rexCrs.submit_order(customer, payment=payment, bookings=bookings, payerInfo=payerInfo,
		                                 otherItems=None)
		return salesOrder

	except Exception as exc:
		if 'AVS:N' in str(exc):
			messages.append("AVS Error: Please check your billing address. It must match what is on file with your credit card company.")
		else:
			messages.append(exc)

	return None


def buildTripsForBookingSession(bookSession, originId, destinationId, tripDate, timeFrameKey):
	rexCrs = getRexClient()
	timeFrames = rexCrs.get_trip_timeframes()

	for token in timeFrames:
		if token.key == timeFrameKey:
			timeFrame = token
			break

	originName = getTripLocationName(originId, bookSession.origin_rex_key)
	originToken = RexToken(originId, originName)

	destName = getTripLocationName(destinationId, originId)
	destToken = RexToken(destinationId, destName)

	travellers = buildRexTravellerListForBookSession(bookSession)

	try:
		rexTrips = rexCrs.find_trips(originToken, destToken, tripDate, timeFrame, travellers, None)
	except Exception as e:
		logging.error(e)
		rexTrips = None

	if rexTrips == None:
		try:
			rexTrips = rexCrs.find_trips(originToken, destToken, tripDate, None, travellers, None)
		except Exception as e:
			logging.error(e)
			return

	if bookSession.origin_trip and bookSession.origin_trip.origin_key == originId:
		bookSession.origin_trip = None

	if bookSession.return_trip and bookSession.return_trip.origin_key == originId:
		bookSession.return_trip = None

	bookSession.trips.filter(origin_key=originId).delete()

	if rexTrips:
		for rex_trip in rexTrips:
			trip = models.Trip()
			trip.InitializeFromRexTrip(bookSession, rex_trip)
			trip.save()

			if len(rex_trip.components):
				for rex_comp in rex_trip.components:
					compTrip = models.Trip()
					compTrip.InitializeFromRexTrip(bookSession, rex_comp)
					compTrip.parent = trip
					compTrip.save()

	bookSession.save()


def priceOutBooking(booksession):
	booksession.ticket_total = Decimal('0.00')
	booksession.tax_total = Decimal('0.00')
	booksession.grand_total = Decimal('0.00')
	booksession.discount_total = Decimal('0.00')
	booksession.save()

	all_travelers = booksession.traveler_profiles.all()
	# clear out traveler price breakouts
	for traveller in all_travelers:
		traveller.ticket_total = Decimal('0.00')

	messages = []
	bookings = getProposedBookings(booksession, messages)

	#If a discount code was given then apply it to each reservation
	if len(booksession.promo_code) > 1:
		bookings = applyPromoCodeToBookings(booksession.promo_code, bookings)

	if bookings == None:
		logging.error('No bookings returned!')
		return

	# total up charges
	for booking in bookings:
		if booking.billing == None:
			logging.error("billing missing!")
			continue

		subtotal_string = str(booking.billing.subtotal.amount)
		taxes_string = str(booking.billing.taxes.amount)
		total_string = str(booking.billing.total.amount)
		discount_string = str(booking.billing.discounts.amount)

		booksession.ticket_total += Decimal(subtotal_string)
		booksession.tax_total += Decimal(taxes_string)
		booksession.grand_total += Decimal(total_string)
		booksession.discount_total += Decimal(discount_string)

		# get price breakout per traveller
		for reservation in booking.reservations:
			rsrv_price = reservation.billed.amount

			for traveller in all_travelers:
				# Rex requires our ids to be negative so that it does not
				# attempt a lookup
				if str(-1 * traveller.id) == reservation.traveler.key:
					traveller.ticket_total += rsrv_price
					break


	# Save all changes
	for traveller in all_travelers:
		traveller.save()

	booksession.pickled_rex_booking_session = pickle.dumps(bookings)
	booksession.save()

def applyPromoCodeToBookings(promoCode, bookings):
	modifiedBookings = []

	# Remove existing promo codes
	for booking in bookings:
		for reservation in booking.reservations:
			redemptionsToRemove = []

			for redemption in reservation.redemptions:
				if redemption.type == 'Discount':
					redemptionsToRemove.append(redemption)

			for redemption in redemptionsToRemove:
				reservation.redemptions.remove(redemption)

	rexCrs = getRexClient()
	try:
		discount = rexCrs.fetch_discount(promoCode)
	except NotFoundException:
		return None

	for booking in bookings:
		for reservation in booking.reservations:
			reservation.discount(discount)

		repricedBooking = rexCrs.requote(booking)
		modifiedBookings.append(repricedBooking)

	return modifiedBookings


def getProposedBookings(bookSession, messages):
	bookings = []

	if bookSession.origin_trip != None:
		rexBooking = getRexBookingForTrip(bookSession.origin_trip, messages)
		if rexBooking:
			setSeatingAssignmentsForBooking(rexBooking, bookSession.origin_trip)
			bookings.append(rexBooking)

	if bookSession.return_trip != None:
		rexBooking = getRexBookingForTrip(bookSession.return_trip, messages)
		if rexBooking:
			setSeatingAssignmentsForBooking(rexBooking, bookSession.return_trip)
			bookings.append(rexBooking)

	return bookings


# Match up chosen seat no's with the seats available for this trip.
def setSeatingAssignmentsForBooking(rexBooking, trip):
	try:
		rexCrs = getRexClient()
		availSeats = rexCrs.fetch_available_seats(rexBooking)

		for reservation in rexBooking.reservations:
			for assgn in trip.seat_assignments.all():
				if assgn.seat_no == None or assgn.seat_no == 'None':
					continue
				if str(-1 * assgn.travelerProfile_id) == reservation.traveler.key:
					reservation.assign_to(assgn.seat_no)

	except Exception as exc:
		logging.error(exc)



def getRexBookingForTrip(trip, messages):
	rexBooking = None

	try:
		rexCrs = getRexClient()

		rexFacility = RexToken(trip.facility_key, trip.facility_name)
		rexProduct = RexToken(trip.product_key, trip.product_name)
		rexOrigin = RexToken(trip.origin_key, trip.origin_name)
		rexDest = RexToken(trip.destination_key, trip.destination_name)
		rexTrip = RexTrip(rexFacility, rexProduct, rexOrigin, rexDest, trip.depart_date,
		                  trip.depart_time, trip.arrive_date, trip.arrive_time,
		                  trip.carrier_name, trip.route_name)

		rexTrip.crs = trip.rex_crs

		#add component legs if there are any
		if trip.hasComponentTripLegs():
			rexTrip.components = []

			for tripLeg in trip.trip_legs.all():
				rexFacility = RexToken(tripLeg.facility_key, tripLeg.facility_name)
				rexProduct = RexToken(tripLeg.product_key, tripLeg.product_name)
				rexOrigin = RexToken(tripLeg.origin_key, tripLeg.origin_name)
				rexDest = RexToken(tripLeg.destination_key, tripLeg.destination_name)
				rexTripLeg = RexTrip(rexFacility, rexProduct, rexOrigin, rexDest, tripLeg.depart_date,
				                     tripLeg.depart_time, tripLeg.arrive_date, tripLeg.arrive_time,
				                     tripLeg.carrier_name, tripLeg.route_name)

				rexTripLeg.crs = tripLeg.rex_crs

				rexTrip.components.append(rexTripLeg)

		travellers = buildRexTravellerListForBookSession(trip.bookTripSession)
		rexBooking = rexCrs.propose_trip_booking(rexTrip, travellers)

	except Exception as e:
		logging.error(e)
		messages.append(e)
		pass

	return rexBooking


def buildRexTravellerListForBookSession(bookSession):
	travellers = []

	for traveller in bookSession.traveler_profiles.all():
		rexTrav = RexTraveler((-1) * traveller.id)

		rexTrav.first_name = traveller.first_name
		rexTrav.last_name = traveller.last_name
		rexTrav.phone = traveller.phone


		# Default age unless specified
		if traveller.traveler_class == 'ADULT':
			rexTrav.age = 30

		if traveller.traveler_class == 'CHILD':
			rexTrav.age = 8

		if traveller.traveler_class == 'STUDENT':
			rexTrav.age = 16
			rexTrav.student = True

		if traveller.traveler_class == 'SENIOR':
			rexTrav.age = 70

		if traveller.age > 0:
			rexTrav.age = traveller.age

		travellers.append(rexTrav)

	return travellers


def getTripLocationName(location_token, origin_token):
	rexCrs = getRexClient()
	origins = rexCrs.get_trip_origins()

	for origin in origins:
		if location_token == origin.key:
			return origin.name


	# if not found then get destinations for the origin
	destinations = rexCrs.get_trip_destinations(origin_token)
	for dest in destinations:
		if location_token == dest.key:
			return dest.name

	return None


def buildDictionaryOfLocations(locations):
	locationDict = {}

	for token in locations:
		locationDict[token.key] = token.name

	return locationDict

