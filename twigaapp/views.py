import os
import json
import logging
import requests
from decouple import config
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import logout
from django.db.models import Count, Q
from requests.auth import HTTPBasicAuth
from twigaapp.forms import ImageUploadForm, ManagersForm
from requests import HTTPError, RequestException, Timeout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from twigaapp.credentials import MpesaAccessToken, LipanaMpesaPassword
from twigaapp.models import Contacts, Bookings, ImageModels, Users, Managers



def index(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            user = Users.objects.get(username=username)
            if check_password(password, user.password):
                return render(request, 'index.html')
            else:
                messages.error(request, 'Incorrect password.')
                return render(request, 'login.html', {
                    'username': request.POST['username']
                })
        except Users.DoesNotExist:
            messages.error(request, 'User profile not found.')
            return redirect('login')
    else:
        return render(request, 'login.html')


def register(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'register.html', {
                'username': request.POST['username'],
                'phone': request.POST['phone'],
                'email': request.POST['email']
            })
        hashed_password = make_password(password)
        new_user = Users(
            username=request.POST['username'],
            phone=request.POST['phone'],
            email=request.POST['email'],
            password=hashed_password,
        )
        new_user.save()
        return redirect('/login')
    return render(request, 'register.html')


def login(request):
    return render(request, 'login.html')


def services(request):
    return render(request, 'services.html')


def bookings(request):
    if request.method == 'POST':
        phone = request.POST['phone']
        amount = request.POST['amount']
        mpesa_status = stk(phone, amount)
        new_booking = Bookings(
            type=request.POST['type'],
            mpesaRequestSent=mpesa_status,
            name=request.POST['name'],
            phone=phone,
            email=request.POST['email'],
            dateBooked=request.POST['dateTime'],
            persons=request.POST['persons'],
            specialRequest=request.POST['specialRequest'],
        )
        new_booking.save()
        if mpesa_status:
            messages.success(request, 'Your booking has been sent successfully! Mpesa request sent successfully!')
        else:
            messages.warning(request, 'Your booking has been sent successfully, but Mpesa request failed. Please try again later.')
        return redirect('/bookings#booking_tabs')
    return render(request, "bookings.html")


def menu(request):
    return render(request, 'menu.html')


def about(request):
    return render(request, 'about.html')


def contact(request):
    if request.method == 'POST':
        new_contact = Contacts(
            name=request.POST['name'],
            phone=request.POST['phone'],
            email=request.POST['email'],
            subject=request.POST['subject'],
            message=request.POST['message'],
        )
        new_contact.save()
        messages.success(request, 'Your message has been sent successfully!')
        return redirect('/contact#contact_heading')
    else:
        return render(request, 'contact.html')


def gallery(request):
    images = ImageModels.objects.all().order_by('-id')
    return render(request, 'gallery.html', {'images': images})


def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('/gallery#twiga_gallery')
        else:
            return render(request, 'gallery.html', {'form': form})
    else:
        form = ImageUploadForm()
    return render(request, 'gallery.html', {'form': form})


def image_delete(request, id):
    image = ImageModels.objects.get(id=id)
    image.delete()
    return redirect('/gallery#twiga_gallery')











def token(request):
    consumer_key = config('CONSUMER_KEY')
    consumer_secret = config('CONSUMER_SECRET')
    api_URL = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    r = requests.get(api_URL, auth=HTTPBasicAuth(consumer_key, consumer_secret))
    mpesa_access_token = json.loads(r.text)
    validated_mpesa_access_token = mpesa_access_token["access_token"]
    return render(request, 'token.html', {"token": validated_mpesa_access_token})

def stk(phone, amount):
    print(f"Attempting Mpesa request with phone: {phone} and amount: {amount}")
    access_token = MpesaAccessToken.validated_mpesa_access_token
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": "Bearer %s" % access_token}
    request = {
        "BusinessShortCode": LipanaMpesaPassword.Business_short_code,
        "Password": LipanaMpesaPassword.decode_password,
        "Timestamp": LipanaMpesaPassword.lipa_time,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": LipanaMpesaPassword.Business_short_code,
        "PhoneNumber": phone,
        "CallBackURL": "https://sandbox.safaricom.co.ke/mpesa/",
        "AccountReference": "Twiga Resort",
        "TransactionDesc": "Twiga Reservation Charges"
    }
    try:
        response = requests.post(api_url, json=request, headers=headers)
        print("Here is the response from try true")
        print(f"Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
        if response.status_code == 200:
            return True
        else:
            return False
    except (Timeout, HTTPError, RequestException) as e:
        logging.error(f"Error during Mpesa request: {e}")
        return False



def mgr_edit_image(request, manager_id):
    manager = get_object_or_404(Managers, id=manager_id)
    if request.method == 'POST' and request.FILES.get('image'):
        new_image = request.FILES['image']
        if manager.image:
            old_image_path = manager.image.path
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
        manager.image = new_image
        manager.save()
        return redirect('managers')
    return redirect('managers')




def mgr_delete_image(request, manager_id):
    manager = get_object_or_404(Managers, id=manager_id)
    if manager.image:
        old_image_path = manager.image.path
        if os.path.exists(old_image_path):
            os.remove(old_image_path)
    manager.image = None
    manager.save()
    return redirect('managers')


# Dashboard Functions

def manager_register(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'twiga_management/register.html', {
                'manager_name': request.POST['manager_name'],
                'phone': request.POST['phone'],
                'email': request.POST['email'],
                'image': request.FILES.get('image')
            })
        new_manager = Managers(
            manager_name=request.POST['manager_name'],
            phone=request.POST['phone'],
            email=request.POST['email'],
            image=request.FILES.get('image', None),
            password=make_password(request.POST['password']),
        )
        new_manager.save()
        return redirect('/manager_login')
    return render(request, 'twiga_management/register.html')

def manager_login(request):
    if request.method == 'POST':
        manager_name = request.POST.get('manager_name')
        password = request.POST.get('password')
        try:
            all_managers = Managers.objects.filter(manager_name=manager_name)
            for manager in all_managers:
                if check_password(password, manager.password):
                    request.session['manager_id'] = manager.id
                    request.session.save()
                    return redirect('dashboard')
            messages.error(request, 'Invalid password.')
        except Managers.DoesNotExist:
            messages.error(request, 'Manager not found.')
    return render(request, 'twiga_management/login.html')


def dashboard(request):
    manager_id = request.session.get('manager_id')
    print(f"Retrieved manager_id from session: {manager_id}")
    if not manager_id:
        print('Cannot find manager_id')
        messages.error(request, 'You must be logged in to access the dashboard.')
        return redirect('manager_login')
    manager = get_object_or_404(Managers, id=manager_id)
    all_managers = Managers.objects.all().order_by('-id')
    all_users = Users.objects.all().order_by('-id')

    all_bookings = Bookings.objects.all().order_by('-id')
    total_bookings = all_bookings.count()
    bookings_by_type = (
        all_bookings.values('type')
        .annotate(type_count=Count('type'))
        .order_by('type')
    )
    bookings_by_type_dict = {entry['type']: entry['type_count'] for entry in bookings_by_type}
    special_request_count = all_bookings.filter(specialRequest__isnull=False).exclude(specialRequest='').count()
    mpesa_sent_count = all_bookings.filter(mpesaRequestSent=True).count()
    mpesa_not_sent_count = total_bookings - mpesa_sent_count
    today = timezone.now().date()
    today_bookings = all_bookings.filter( Q(dateBooked__date=today) )
    today_bookings_count = today_bookings.count()

    all_contacts = Contacts.objects.all().order_by('-id')
    total_contacts = Contacts.objects.count()
    contacts_with_message = all_contacts.filter(message__isnull=False).exclude(message='').count()
    contacts_without_message = total_contacts - contacts_with_message

    return render(request, 'twiga_management/dashboard.html', {
        'bookings': all_bookings,
        'contacts': all_contacts,
        'users': all_users,
        'managers': all_managers,
        'manager': manager,
        'total_contacts': total_contacts,
        'contacts_with_message': contacts_with_message,
        'contacts_without_message': contacts_without_message,
        'total_bookings': total_bookings,
        'bookings_by_type': bookings_by_type_dict,
        'special_request_count': special_request_count,
        'mpesa_sent_count': mpesa_sent_count,
        'mpesa_not_sent_count': mpesa_not_sent_count,
        'today_bookings': today_bookings,
        'today_bookings_count': today_bookings_count,
    })



# Managers
def managers(request):
    manager_id = request.session.get('manager_id')
    if not manager_id:
        print('Cannot find manager_id for managers.function in views')
        messages.error(request, 'You must be logged in to access the twiga managers.')
        return redirect('manager_login')
    manager = Managers.objects.get(id=manager_id)
    all_managers = Managers.objects.all().order_by('-id')
    return render(request, 'twiga_management/managers.html', {
        'manager': manager,
        'managers': all_managers
    })


def manager_update(request, id):
    manager_update_info = Managers.objects.get(id=id)
    form = ManagersForm(request.POST, request.FILES or None, instance=manager_update_info)

    if form.is_valid():
        form.save()
        messages.success(request, 'Manager details updated successfully.')
        return redirect('managers')

    # Handle invalid form submission
    manager_id = request.session.get('manager_id')
    if not manager_id:
        messages.error(request, 'You must be logged in to access the managers page.')
        return redirect('manager_login')

    messages.error(request, 'Failed to update manager details. Please correct the errors below.')
    print("Error updating manager details\n")
    print("Form errors:", form.errors)
    return render(request, 'twiga_management/managers.html')


def manager_delete(request, id):
    manager = Managers.objects.get(id=id)
    if request.session.get('manager_id') == id:
        if manager.image:
            image_path = manager.image.path
            if os.path.exists(image_path):
                os.remove(image_path)
        logout(request)
        request.session.flush()
        manager.delete()
        return redirect('manager_login')

    manager.delete()
    print(f"Manager {manager.manager_name} (ID: {manager.id}) deleted by another user.")
    return redirect('managers')


def manager_logout(request):
    logout(request)
    return redirect('manager_login')



# Bookings
def booking_delete(request, id):
    single_booking = Bookings.objects.get(id=id)
    single_booking.delete()
    return redirect('/dashboard#bookings-table')



# Contacts
def delete_contact(request, id):
    single_contact = Contacts.objects.get(id=id)
    single_contact.delete()
    return redirect('/dashboard#contacts-table')



# Users
def users(request):
    manager_id = request.session.get('manager_id')
    if not manager_id:
        print('Cannot find manager_id for users.function in views')
        messages.error(request, 'You must be logged in to access the twiga users.')
        return redirect('manager_login')
    manager = Managers.objects.get(id=manager_id)
    all_users = Users.objects.all().order_by('-id')
    return render(request, 'twiga_management/users.html', {
        'manager': manager,
        'users': all_users
    })


def user_delete(request, id):
    user = Users.objects.get(id=id)
    user.delete()
    return redirect('/users')


def documentation(request):
    manager_id = request.session.get('manager_id')
    if not manager_id:
        # If no manager_id is found in session, redirect to login page
        print('Cannot find manager_id for documentation.function in views')
        messages.error(request, 'You must be logged in to access the documentation.')
        return redirect('manager_login')
    # Fetch the logged-in manager's details
    manager = Managers.objects.get(id=manager_id)
    # Pass the manager object to the template
    return render(request, 'twiga_management/documentation.html', {
        'manager': manager
    })







def test(request):
    return render(request, 'test.html')