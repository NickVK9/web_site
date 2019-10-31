import logging
from django.contrib.auth.decorators import login_required
from decorators import customer_login_required
from django.shortcuts import render_to_response
from registration.forms import CorporateRegistrationForm, IndividualRegistrationForm, CreateAccountForm, ModifyAccountForm
from rexweb.crm import customer
from webapp.utility import setDetailContext
from django.template import RequestContext
from book_trip.forms import *
from rexHelperFunctions import *
from forms import EditTravellerProfileForm, AddTravellerProfileForm, CreditCardEditForm



@customer_login_required
def viewDashboard(request):

	context = {}
	setDetailContext(context, request)

	return render_to_response('customer_dashboard/dashboard.html', context, context_instance=RequestContext(request))



@customer_login_required
def viewReservations(request):

	context = {}
	setDetailContext(context, request)

	rexCrm = getRexCRM()
	userProfile = context['userProfile']
	rexCustomer = userProfile.rex_customer()

	rexReservations = rexCrm.fetch_sales_records_for(rexCustomer)
	context['reservations'] = rexReservations

	return render_to_response('customer_dashboard/reservations.html', context, context_instance=RequestContext(request))



@customer_login_required
def viewTickets(request):

	context = {}
	setDetailContext(context, request)

	try:
		ticketPacks = context['userProfile'].get_rex_ticket_packs()
	except Exception as exc:
		logging.error(exc)
		ticketPacks = None

	context['ticketPacks'] = ticketPacks

	return render_to_response('customer_dashboard/tickets.html', context, context_instance=RequestContext(request))



@customer_login_required
def viewAccountInfo(request):

	modifyAccountForm = None
	individualRegistrationForm = None
	corporateRegistrationForm = None

	userProfile = request.userProfile
	rexCustomer = userProfile.rex_customer()
	account_type = rexCustomer.kind

	if request.method == 'POST':
		#modifyAccountForm = ModifyAccountForm(request.POST)

		if account_type == 'consumer':
			individualForm = IndividualRegistrationForm(request.POST)
		else:
			corporateForm = CorporateRegistrationForm(request.POST)

		rexCrm = getRexCRM()

		if account_type == 'consumer' and individualForm.is_valid():
			cleaned_data = individualForm.cleaned_data

			custChanges = RexCustomer(key=cleaned_data['key'], account_name=rexCustomer.account_name)
			custChanges.webUsername = rexCustomer.webUsername
			custChanges.firstName = cleaned_data['firstName']
			custChanges.lastName = cleaned_data['lastName']
			custChanges.street = cleaned_data['street']
			custChanges.street2 = cleaned_data['street2']
			custChanges.city = cleaned_data['city']
			custChanges.state = cleaned_data['state']
			custChanges.postal = cleaned_data['postal']
			custChanges.country = cleaned_data['country']
			custChanges.email = cleaned_data['email']
			custChanges.phoneDay = cleaned_data['phoneDay']
			custChanges.phoneEve = cleaned_data['phoneEve']

			try:
				rexCrm.update_customer(custChanges)
				# Reload rex customer to see if changes took
				rexCustomer = userProfile.rex_customer()
			except Exception as ex:
				print ex



	context = {'rexCustomer':rexCustomer}
	setDetailContext(context, request)

	modifyAccountForm = ModifyAccountForm(data=rexCustomer.__dict__)
	context['modifyAccountForm'] = modifyAccountForm

	if account_type == 'consumer':
		individualRegistrationForm = IndividualRegistrationForm(data=rexCustomer.__dict__)
		context['individualRegistrationForm'] = individualRegistrationForm

	if account_type == 'reseller':
		corporateRegistrationForm = CorporateRegistrationForm(data=rexCustomer.__dict__)
		context['corporateRegistrationForm'] = corporateRegistrationForm

	return render_to_response('customer_dashboard/account_info.html', context, context_instance=RequestContext(request))



@customer_login_required
def viewCards(request):

	userProfile = request.userProfile
	rexCustomer = userProfile.rex_customer()


	if request.method == 'POST':
		creditCardForm = CreditCardEditForm(request.POST)

		if creditCardForm.is_valid():
			cleaned_data = creditCardForm.cleaned_data

			expMonth = cleaned_data['exp_month']
			expYear = cleaned_data['exp_year'][2:]
			expiry = "%s/%s" % (expMonth, expYear)
			key = cleaned_data['key']

			if key == '0':
				addCreditCardOnFile(rexCustomer,cleaned_data['holder'],
			                    cleaned_data['number'],
			                    expiry)
			else:
				modifyCreditCardOnFile(rexCustomer,key, cleaned_data['holder'],
			                    cleaned_data['number'],
			                    expiry)

			creditCardForm = CreditCardEditForm()

	else:
		creditCardForm = CreditCardEditForm(data={'key':0,})

	context = {'creditCardForm': creditCardForm}
	setDetailContext(context, request)

	rexCrm = getRexCRM()
	rexCards = rexCrm.fetch_credit_cards_for(rexCustomer)
	context['creditCards'] = rexCards

	return render_to_response('customer_dashboard/cards.html', context, context_instance=RequestContext(request))

@customer_login_required
def deleteCard(request, cardKey):
	userProfile = request.userProfile
	rexCustomer = userProfile.rex_customer()


	deleteCreditCardOnFile(rexCustomer, cardKey)

	return HttpResponseRedirect(reverse(viewCards))

	


@customer_login_required
def addProfile(request):
	context = {}
	setDetailContext(context, request)
	if request.method == 'POST':
		addTravellerForm = AddTravellerProfileForm(request.POST)

		if addTravellerForm.is_valid():

			cleaned_data = addTravellerForm.cleaned_data
			try:
				userProfile = context['userProfile']
				newRexProfile = addTravellerProfile(userProfile.rex_customer_key,cleaned_data)
			except Exception as exc:
				logging.error(exc)
				
	request.method = 'GET'
	return viewProfiles(request)


@customer_login_required
def viewProfiles(request):

	editForm = None


	if request.method == 'POST':
		editForm = EditTravellerProfileForm(request.POST)

		if editForm.is_valid():
			cleaned_data = editForm.cleaned_data

			rexCrm = getRexCRM()

			rexProfile = RexProfile(key=cleaned_data['key'])
			rexProfile.firstName = cleaned_data['firstName']
			rexProfile.lastName = cleaned_data['lastName']
			rexProfile.street = cleaned_data['street']
			rexProfile.street2 = cleaned_data['street2']
			rexProfile.city = cleaned_data['city']
			rexProfile.state = cleaned_data['state']
			rexProfile.postal = cleaned_data['postal']
			rexProfile.country = cleaned_data['country']
			rexProfile.phoneDay = cleaned_data['phoneDay']
			rexProfile.phoneEve = cleaned_data['phoneEve']
			rexProfile.email = cleaned_data['email']
			
			consumer = rexCrm.update_profile(rexProfile)
			editForm = EditTravellerProfileForm()

	else:
		editForm = EditTravellerProfileForm()

	addTravellerForm = AddTravellerProfileForm()

	context = {'editForm': editForm,  'addTravellerForm':addTravellerForm,}
	setDetailContext(context, request)
	
	userProfile = context['userProfile']
	rexProfiles = getCompleteCustomerProfiles(userProfile.rex_customer_key, userProfile.rex_customer_name)

	context['travellerProfiles'] = rexProfiles

	return render_to_response('customer_dashboard/profiles.html', context, context_instance=RequestContext(request))



@customer_login_required
def viewHistory(request):

	context = {}
	setDetailContext(context, request)

	rexCrm = getRexCRM()
	userProfile = context['userProfile']
	rexCustomer = userProfile.rex_customer()

	transactions = rexCrm.fetch_sales_records_for(rexCustomer)
	context['transactions'] = transactions

	return render_to_response('customer_dashboard/history.html', context, context_instance=RequestContext(request))


