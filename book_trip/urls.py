from django.conf.urls import include, url
from book_trip.views import select_trip, trip_details, name_passengers, billme, checkout, order_complete, send_email_invoice

urlpatterns = [
   url(r'^$', select_trip),
   url(r'^trip-details', trip_details),
   url(r'^select-trip', select_trip),
   url(r'^name-passengers', name_passengers),
   url(r'^billme$', billme),
   url(r'^checkout$', checkout),
   url(r'^order-complete', order_complete, name='order-complete'),
   url(r'^send-email-invoice', send_email_invoice),
]
