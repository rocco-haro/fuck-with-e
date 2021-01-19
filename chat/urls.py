from django.urls import path
from .views import index, twilioNumbers, login, logout, buy_twilio_number, sms

urlpatterns = [
    path('', index, name="index"),
    # path('<target_number>/<twilio_number>', index, name="index"),
    path('<target_number>_<twilio_number>', index, name="index"),
    # path('twilio_numbers', twilio_numbers, name="twilio_numbers"),
    path('t-numbers', twilioNumbers, name="twilioNumbers"),
    path('login', login, name="login"),
    path('logout', logout, name="logout"),

    path('buy_twilio_number/<number>', buy_twilio_number, name="buy_twilio_number"),
    path('sms', sms, name="sms"),
]