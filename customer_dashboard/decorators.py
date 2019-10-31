from django.contrib.auth import logout
from django.http import HttpResponseRedirect


def customer_login_required(function=None):
	def wrap(request, *args, **kwargs):
		if not request.userProfile:
			logout(request)
			return HttpResponseRedirect('/userLogin/')

		return function(request, *args, **kwargs)
	wrap.__doc__=function.__doc__
	wrap.__name__=function.__name__
	return wrap

