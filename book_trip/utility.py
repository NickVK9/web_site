from rexweb.crs.crs import RexCRS
from rexweb.core.generic import User as RexUser
from rexweb.ws.rexapi import RexAPI
from django.conf import settings
from rexweb.ext.django.cache import DjangoCache

_djangoCache = DjangoCache()


def getRexClient():

	#crs = RexCRS( MockRex() )
	crs = RexCRS(RexAPI(settings.REX_URL))
	crs.set_cache(_djangoCache)
	# log in as the website (not the website's user, if there is one)
	user = RexUser(settings.REX_USER,settings.REX_PASSWORD)
	crs.login( user )

	return crs

