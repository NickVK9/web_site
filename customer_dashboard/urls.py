from django.conf.urls.defaults import *

urlpatterns = patterns('customer_dashboard.views',
    (r'^$','viewDashboard'),
	(r'^reservations/$','viewReservations'),
	(r'^tickets/$','viewTickets'),
	(r'^account_info/$','viewAccountInfo'),
	(r'^cards/$','viewCards'),
    (r'^cards/delete/(?P<cardKey>.*)$','deleteCard'),
	(r'^profiles/$','viewProfiles'),
	(r'^addNewProfile/$','addProfile'),
	(r'^history/$','viewHistory'),
)
