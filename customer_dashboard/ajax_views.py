import simplejson as json
from django.contrib.auth.decorators import login_required
from decorators import customer_login_required
from django.http import HttpResponse
from django.template import RequestContext
from django.template.loader import render_to_string
from rexHelperFunctions import *
from models import UserProfile
from forms import EditTravellerProfileForm, CreditCardEditForm

@login_required
@customer_login_required
def editProfile(request):
	json_data={}

	if request.POST:

		personKey = request.POST['profileId']
		userProfile = UserProfile.objects.get(user=request.user)
		rexProfiles = getCompleteCustomerProfiles(userProfile.rex_customer_key, userProfile.rex_customer_name)

		foundProfile = None

		# Pick out the traveller profile we are editing
		for profile in rexProfiles:
			if profile.personKey == personKey:
				foundProfile = profile
				break


		#initialData = {'first_name':foundProfile.firstName,}
		editForm = EditTravellerProfileForm(data=foundProfile.__dict__)

		context = {'form':editForm,}
		html = render_to_string('customer_dashboard/edit_profile_template.html', context, context_instance=RequestContext(request))
		json_data['html'] = html


	return HttpResponse(json.dumps(json_data),mimetype='application/json')










@login_required
@customer_login_required
def editCard(request):
	json_data={}

	if request.POST:

		cardKey = request.POST['cardKey']
		userProfile = request.userProfile
		rexCustomer = userProfile.rex_customer()

		cards = getCreditCardsOnFile(rexCustomer)

		foundCard = None

		# Pick out the traveller profile we are editing
		for card in cards:
			if card.key == cardKey:
				foundCard = card
				break


		if foundCard:

			dataDict = {'holder':foundCard.holder,'brand':foundCard.brand,}

			# Split card type from number
			parts = foundCard.number.split(' ')
			if len(parts) > 1:
				number = parts[1]
			else:
				number = foundCard.number

			dataDict['number'] = number

			# Split expire date apart
			dateParts = foundCard.expiry.split('/')
			if len(dateParts) ==2:
				month = dateParts[0]
				year = '20%s' % dateParts[1]
			else:
				month = '01'
				year = '2000'

			dataDict['exp_month'] = month
			dataDict['exp_year'] = year
			dataDict['key'] = foundCard.key

			editForm = CreditCardEditForm(data=dataDict)
		else:
			editForm = CreditCardEditForm()

		context = {'creditCardForm':editForm,}
		html = render_to_string('customer_dashboard/edit_card_template.html', context,
		                        context_instance=RequestContext(request))
		
		json_data['html'] = html


	return HttpResponse(json.dumps(json_data),mimetype='application/json')



