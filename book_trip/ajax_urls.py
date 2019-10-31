from django.conf.urls import include, url
from book_trip.ajax_views import getDestinations, findTrips, refreshOriginTrips, refreshReturnTrips, getSeatingForTrip, getTravelerProfile, saveTravelerProfile, linkTravelerProfile, tripSelected, getPassengerList, assignPassengerToSeat, refreshPrice, setOrigin, setDestination, setReturnOrigin, setDepartureDate, setReturnDate, applyCoupon, getHelpText, checkForTripAlert


urlpatterns = [
                       url(r'^get-destinations$',getDestinations),
                       url(r'^find-trips$',findTrips),
                       url(r'^refresh-origin-trips$',refreshOriginTrips),
                       url(r'^refresh-return-trips',refreshReturnTrips),
                       url(r'^get-seating-for-trip$',getSeatingForTrip),
					   url(r'^get-traveler-profile$',getTravelerProfile),
					   url(r'^save-traveler-profile$',saveTravelerProfile),
					   url(r'^link-traveler-profile$',linkTravelerProfile),
                       url(r'^trip_selected', tripSelected),
                       url(r'^get-passenger-list',getPassengerList),
                       url(r'^assign_passenger_to_seat',assignPassengerToSeat),
                       url(r'^refresh-price',refreshPrice),
                       url(r'^set-origin',setOrigin),
                       url(r'^set-destination',setDestination),
                       url(r'^set-return-origin',setReturnOrigin),
                       url(r'^set-departure-date',setDepartureDate),
                       url(r'^set-return-date',setReturnDate),
                       url(r'^apply_coupon',applyCoupon),
					   url(r'^get-help-text',getHelpText),
                       url(r'^check-for-trip-alert',checkForTripAlert)
]