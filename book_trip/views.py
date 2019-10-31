from datetime import date
import logging

from django.db.models import Q
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect

from django.urls import reverse

from rexweb.crs.order import PayerInfo
from survey.models import Survey
from book_trip import forms #import *
from book_trip import models #import *
from customer_dashboard.models import UserProfile
from book_trip import rexHelperFunctions #import *
from webapp.sslDecorator import secure_required
from webapp.utility import getRexClient, setDetailContext

logger = logging.getLogger(__name__)


def trip_details(request):
	book_session = get_current_booking_session(request)
	rexCrs = getRexClient()
	context = {}

	if request.method == 'POST':
		timeFrames = rexCrs.get_trip_timeframes()
		bookNowForm = forms.BookNowForm(timeFrames, data=request.POST, instance=book_session)

		if book_session.departure_date == None:
			book_session.departure_date = date.today()

		# if book_session.return_date == None:
		#			book_session.return_date = book_session.departure_date + timedelta(days=1)

		if bookNowForm.is_valid():

			book_session.ticket_total = Decimal('0.00')
			book_session.tax_total = Decimal('0.00')
			book_session.grand_total = Decimal('0.00')

			book_session.origin_trip = None
			book_session.return_trip = None
			book_session.origin_label = getTripLocationName(book_session.origin_rex_key, None)
			book_session.destination_label = getTripLocationName(book_session.destination_rex_key,
			                                                     book_session.origin_rex_key)

			book_session.save()
			# process passengers
			book_session.initialize_traveler_profiles()

			# clear out traveler price breakouts
			for traveller in book_session.traveler_profiles.all():
				traveller.ticket_total = Decimal('0.00')
				traveller.save()

			# Departure Trips
			buildTripsForBookingSession(book_session, book_session.origin_rex_key,
			                            book_session.destination_rex_key,
			                            book_session.departure_date,
			                            book_session.departure_time)

			# Return Trips
			buildTripsForBookingSession(book_session, book_session.destination_rex_key,
			                            book_session.origin_rex_key,
			                            book_session.return_date,
			                            book_session.return_time)
			# return select_trip(request)
			return HttpResponseRedirect(reverse(select_trip))

		else:
			context['bookNowForm'] = bookNowForm

	if book_session.origin_rex_key != None:
		destinations = rexCrs.get_trip_destinations(book_session.origin_rex_key)
	else:
		destinations = None

	context['bookSession'] = book_session
	context['destinations'] = destinations
	setDetailContext(context, request)

	return render_to_response('book_trip/trip_details.html', context)


def select_trip(request):
	message = None
	book_session = get_current_booking_session(request)
	rexCrs = getRexClient()

	origins = rexCrs.get_trip_origins()

	if book_session.origin_rex_key != None:
		destinations = rexCrs.get_trip_destinations(book_session.origin_rex_key)
	else:
		destinations = None

	context = {'origins': origins, 'destinations': destinations,
	           'bookSession': book_session, 'message': message, }

	setDetailContext(context, request)

	# If user is logged in then pull any traveler profiles on the account
	if context.has_key('userProfile') and None is not context['userProfile']:
		try:
			rexProfiles = context['userProfile'].rex_traveller_profiles()
			context['travelerProfiles'] = rexProfiles
		except Exception as exc:
			logging.error(exc)

	return render_to_response('book_trip/book_trip.html', context, context_instance=RequestContext(request))


def name_passengers(request):
	book_session = get_current_booking_session(request)

	context = {'bookSession': book_session}
	setDetailContext(context, request)

	for traveler in book_session.traveler_profiles.all():
		if traveler.last_name[:5] == "ADULT":
			traveler.last_name = "PASSENGER" + traveler.last_name[5:]
			traveler.save()
		print(traveler)



	return render_to_response('book_trip/name_passengers.html', context, context_instance=RequestContext(request))


def billme(request):
	book_session = get_current_booking_session(request)
	messages = None

	if request.method == 'POST':
		userProfile = UserProfile.objects.get(user=request.user)
		customer = userProfile.rex_customer()
		messages = []

		salesOrder = payForBooking(book_session, None, customer, None, messages)

		if salesOrder:
			book_session.sales_order_rex_key = salesOrder.key
			book_session.status = 'CLOSED'
			book_session.save()
			request.session['book_trip_completed_session_id'] = book_session.id

			return HttpResponseRedirect(reverse(order_complete))

	return checkout(request)


@secure_required
def checkout(request):
	book_session = get_current_booking_session(request)
	messages = []
	message = None
	rexCustomer = None

	if request.user.is_authenticated():

		try:
			userProfile = UserProfile.objects.get(user=request.user)
			rexCustomer = userProfile.rex_customer()
		except Exception as exc:
			logger.error(exc)

	if request.method == 'POST':
		payment_form = PaymentForm(data=request.POST)
		payment_form.is_valid()
		payerInfo = None
		try:
			bill_to_email = payment_form.cleaned_data['email']
			full_name = "%s %s" % (payment_form.cleaned_data['first_name'], payment_form.cleaned_data['last_name'])
			payerInfo = PayerInfo(name=full_name, address1=payment_form.cleaned_data['address'],
			                      address2='', city=payment_form.cleaned_data['city'],
			                      state=payment_form.cleaned_data['province_state'],
			                      zip=payment_form.cleaned_data['postal_code'],
			                      country=payment_form.cleaned_data['country'], phone='', email=bill_to_email)
		except KeyError as exc:
			logger.error(exc)

		# 100% off coupon
		if book_session.grand_total <= 0:
			sales_order = payForBooking(book_session, None, rexCustomer, payerInfo, messages)

			if sales_order:
				book_session.sales_order_rex_key = sales_order.key
				book_session.status = 'CLOSED'
				book_session.save()
				request.session['book_trip_completed_session_id'] = book_session.id



				return HttpResponseRedirect(reverse("order-complete"))

		if payment_form.is_valid():
			sales_order = payForBooking(book_session, payment_form, rexCustomer, payerInfo, messages)

			if sales_order:
				book_session.sales_order_rex_key = sales_order.key
				book_session.status = 'CLOSED'
				book_session.save()
				request.session['book_trip_completed_session_id'] = book_session.id

				# If a billto email is available then email it to them
				if bill_to_email:
					try:
						rexCrs = getRexClient()
						rexCrs.send_order_document_email(book_session.sales_order_rex_key, bill_to_email, doc="invoice",
						                                 style="default")
					except Exception as exc:
						logger.error(exc)

				return HttpResponseRedirect(reverse("order-complete"))

			# Could not close the order

	else:
		payment_form = None

	if None == payment_form:
		if None != rexCustomer:
			form_data = {'first_name': rexCustomer.firstName, 'last_name': rexCustomer.lastName,
			             'address': rexCustomer.street,
			             'city': rexCustomer.city, 'province_state': rexCustomer.state, 'country': rexCustomer.country,
			             'postal_code': rexCustomer.postal, }

			payment_form = PaymentForm(data=form_data)
			payment_form._errors = {}
		else:
			payment_form = PaymentForm()

	context = {'trips': [book_session.origin_trip, ], }
	departureLineItemHtml = render_to_string('book_trip/trip_line_items_template.html',
	                                         context, context_instance=RequestContext(request))

	ret_line_html = None
	if book_session.return_trip:
		context = {'trips': [book_session.return_trip, ], }
		ret_line_html = render_to_string('book_trip/trip_line_items_template.html',
		                                      context, context_instance=RequestContext(request))

	context = {'bookSession': book_session, 'paymentForm': payment_form,
	           'departureLineItems': departureLineItemHtml,
	           'returnLineItems': ret_line_html, 'messages': messages, 'message': message}

	setDetailContext(context, request)

	return render_to_response('book_trip/checkout.html', context, context_instance=RequestContext(request))


@secure_required
def order_complete(request):
	completedSessionId = request.session['book_trip_completed_session_id']
	book_session = BookTripSession.objects.get(id=completedSessionId)
	message = None

	if request.method == 'POST':

		email = request.POST['email']

		rexCrs = getRexClient()

		try:
			rexCrs.send_order_document_email(book_session.sales_order_rex_key, email)

			context = {}

			setDetailContext(context, request)

			return render_to_response('book_trip/email_sent.html', context, context_instance=RequestContext(request))
		except:

			message = 'There was a problem sending the email. Please re-enter your email address and try again.'

	context = {'trips': [book_session.origin_trip, ], }
	departureLineItemHtml = render_to_string('book_trip/trip_line_items_template.html',
	                                         context, context_instance=RequestContext(request))

	returnLineItemHtml = None
	if book_session.return_trip:
		context = {'trips': [book_session.return_trip, ], }
		returnLineItemHtml = render_to_string('book_trip/trip_line_items_template.html',
		                                      context, context_instance=RequestContext(request))

	try:
		survey = Survey.objects.filter(
			Q(start_date__lte=datetime.datetime.now) & (Q(end_date=None) | Q(end_date__gte=datetime.datetime.now))
		).order_by('-start_date')[0]

	except:
		survey = None

	context = {'bookSession': book_session, 'departureLineItems': departureLineItemHtml,
	           'returnLineItems': returnLineItemHtml,
	           'message': message, 'survey': survey}

	setDetailContext(context, request)

	return render_to_response('book_trip/order_complete.html', context, context_instance=RequestContext(request))


@secure_required
def send_email_invoice(request):
	completedSessionId = request.session['book_trip_completed_session_id']
	book_session = BookTripSession.objects.get(id=completedSessionId)

	if request.method == 'POST':

		email = request.POST['email']

		rexCrs = getRexClient()

		try:
			rexCrs.send_order_document_email(book_session.sales_order_rex_key, email)

			context = {}

			setDetailContext(context, request)

			return render_to_response('book_trip/email_sent.html', context, context_instance=RequestContext(request))
		except:

			message = 'There was a problem sending the email. Please re-enter your email address and try again.'


def get_current_booking_session(request):
	bookSessionId = request.session.get('book_trip_session_id', None)
	book_session = None

	if bookSessionId:
		try:
			book_session = BookTripSession.objects.get(id=bookSessionId, status='OPEN')
		except:
			book_session = None

	if book_session == None:
		book_session = BookTripSession()
		book_session.save()
		request.session['book_trip_session_id'] = book_session.id

	return book_session
