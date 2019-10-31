from django.conf import settings
from rexweb.core.generic import User as RexUser
from rexweb.crm.crm import RexCRM
from rexweb.crm.customer import Customer as RexCustomer 
from rexweb.crm.traveler import Profile as RexProfile
from rexweb.crm.customer import CardOnFile
from rexweb.ws.rexapi import RexAPI
from rexweb.ext.django.cache import DjangoCache



_djangoCache = DjangoCache()



def deleteCreditCardOnFile(rexCustomer, cardKey):

	rexCrm = getRexCRM()

	cards = rexCrm.fetch_credit_cards_for(rexCustomer)

	foundCard = None
	for card in cards:
		if card.key == cardKey:
			foundCard = card
			break

	if foundCard:
		rexCrm.delete_credit_card(rexCustomer, card)

def modifyCreditCardOnFile(rexCustomer,key, cardHolder, cardNumber, cardExpiry):
	rexCrm = getRexCRM()

	card = CardOnFile(key)
	card.holder = cardHolder
	card.number = cardNumber
	card.expiry = cardExpiry

	rexCrm.update_credit_card( rexCustomer, card )


def addCreditCardOnFile(rexCustomer, cardHolder, cardNumber, cardExpiry):

	rexCrm = getRexCRM()

	card = CardOnFile(None)
	card.holder = cardHolder
	card.number = cardNumber
	card.expiry = cardExpiry

	rexCrm.add_credit_card( rexCustomer, card )



def getCreditCardsOnFile(rexCustomer):

	rexCrm = getRexCRM()
	return rexCrm.fetch_credit_cards_for(rexCustomer)


def getCustomer(rexCustomerKey):
	rexCrm = getRexCRM()
	rexCustomerAcct = RexCustomer(key=rexCustomerKey, account_name="")
	rexCustomer = rexCrm.fetch_customer(rexCustomerAcct)
	return rexCustomer



def getCustomerProfiles(rexCustomerKey,rexCustomerName):
	rexCrm = getRexCRM()
	rexCustomerAcct = RexCustomer(key=rexCustomerKey, account_name=rexCustomerName)
	return rexCrm.fetch_profiles_for(rexCustomerAcct)



def getCompleteCustomerProfiles(rexCustomerKey,rexCustomerName):
	rexCrm = getRexCRM()
	rexCustomerAcct = RexCustomer(key=rexCustomerKey, account_name=rexCustomerName)
	partialProfiles =  rexCrm.fetch_profiles_for(rexCustomerAcct)

	profiles = []

	for partProfile in partialProfiles:
		try:
			profile = rexCrm.fetch_profile(partProfile)
			profiles.append(profile)
		except:
			profiles.append(partProfile)

	return profiles



def filloutTravellerProfile(rexProfile):
	rexCrm = getRexCRM()
	filledProfile = rexCrm.fetch_profile(rexProfile)
	return filledProfile



def getRexTravellerProfileByKey(rexCustomerKey, rexProfileKey):

	partialProfiles = getCustomerProfiles(rexCustomerKey, '')

	for profile in partialProfiles:
		if profile.key == rexProfileKey:
			fullProfile = filloutTravellerProfile(profile)
			return fullProfile

	return None


def getTicketPacks(rexCustomerKey,rexCustomerName):
	rexCrm = getRexCRM()

	rexCustomerAcct = RexCustomer(key=rexCustomerKey, account_name=rexCustomerName)
	ticketPacks = rexCrm.fetch_ticket_coupons(rexCustomerAcct)
	return ticketPacks


def getCustomerPoints(rexCustomerKey,rexCustomerName):
	rexCrm = getRexCRM()

	rexCustomerAcct = RexCustomer(key=rexCustomerKey, account_name=rexCustomerName)
	points = rexCrm.fetch_rewards_balance(customer=rexCustomerAcct)
	return points


def addTravellerProfile(rexCustomerKey, dataDict):
	rexCrm = getRexCRM()
	rexCustomer = getCustomer(rexCustomerKey)

	rexProfile = RexProfile("-1")
	
	rexProfile.firstName = dataDict['firstName']
	rexProfile.lastName = dataDict['lastName']
	rexProfile.phoneDay = dataDict['phoneDay']

	newProfile = rexCrm.create_profile(rexCustomer, rexProfile )

	return newProfile

def getRexCRM():
	rexCrm = RexCRM(RexAPI(settings.REX_URL))
	rexCrm.set_cache(_djangoCache)
	rexUser = RexUser(settings.REX_USER, settings.REX_PASSWORD)
	rexCrm.login(rexUser)

#	rexCrm = RexCRM(MockRex())
#	rexCrm.set_cache(MockCache())
#	rexCrm.login(REX_USER_TESTS)


	return rexCrm
