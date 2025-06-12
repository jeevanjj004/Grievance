from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from grievance_app.models import Grievance  # adjust import if your app name differs

from .forms import CollectorUserForm, CollectorProfileForm
from .models import CollectorProfile
from user.models import User
from core_app.models import Department, District
from officer.models import OfficerProfile

from django.contrib.auth.decorators import login_required

# Auto-generate Collector ID based on district code
def auto_collector_id(district):
    prefix = 'COLL'
    return prefix + str(district.code).upper()


# Create new collector (user + profile)
def create_collector(request):
    user_form = CollectorUserForm(request.POST or None)
    profile_form = CollectorProfileForm(request.POST, request.FILES)

    if request.method == 'POST':
        if user_form.is_valid() and profile_form.is_valid():
            district = profile_form.cleaned_data['district']

            # Create user
            user = user_form.save(commit=False)
            user.username = auto_collector_id(district)
            user.password = make_password(user.password)
            user.user_type = 'COLLECTOR'
            user.is_active = True
            user.date_joined = timezone.now()
            user.save()

            # Create profile
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.collector_id = user.username
            profile.save()

            # Assign to 'collector' group
            collector_group = Group.objects.get(name='collector')
            user.groups.add(collector_group)

            messages.success(request, f"Collector '{user.username}' created successfully.")
            print("Uploaded file:", profile_form.cleaned_data['profile_picture'])

            return redirect('collector:view_collector')
        else:
            print("User form errors:", user_form.errors)
            print("Profile form errors:", profile_form.errors)

    return render(request, 'collector/create_collector.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


# View all collectors
def view_collector(request):
    collectors = CollectorProfile.objects.all()
    return render(request, 'collector/collector_list.html', {'collectors': collectors})



def update_collector(request, username):
    user_instance = get_object_or_404(User, username=username, user_type='COLLECTOR')
    profile_instance = get_object_or_404(CollectorProfile, user=user_instance)

    user_form = CollectorUserForm(request.POST or None, instance=user_instance)
    profile_form = CollectorProfileForm(request.POST or None, request.FILES or None, instance=profile_instance)

    if request.method == 'POST':
        if user_form.is_valid() and profile_form.is_valid():
            district = profile_form.cleaned_data['district']

            user = user_form.save(commit=False)
            user.username = auto_collector_id(district)

            # # ✅ Only set a new password if entered
            # password = user_form.cleaned_data.get('password')
            # if password:
            #     user.set_password(password)

            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user
            profile.collector_id = user.username
            profile.save()

            messages.success(request, f"Collector '{user.username}' updated successfully.")
            return redirect('collector:view_collector')
        else:
            print("User form errors:", user_form.errors)
            print("Profile form errors:", profile_form.errors)

    return render(request, 'collector/update_collector.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


# Delete a collector
def delete_collector(request, username):
    user = get_object_or_404(User, username=username, user_type='COLLECTOR')
    user.delete()
    messages.success(request, f"Collector '{username}' deleted successfully.")
    return redirect('collector:view_collector')


# collector dashboard view

@login_required
def collector_dashboard(request):
    try:
        # Collector info
        collector = CollectorProfile.objects.get(user=request.user)
        district = collector.district

        # Department, district, and collector data
        departments = Department.objects.all()
        districts = District.objects.all()
        collectors = CollectorProfile.objects.all()

        # Grievance counts for that district
        grievances = Grievance.objects.filter(district=district)
        total = grievances.count()
        pending = grievances.filter(status='PENDING').count()
        resolved = total-pending

        context = {
            'departments': departments,
            'districts': districts,
            'collectors': collectors,
            'counts': {
                'total_grievances': total,
                'pending_grievances': pending,
                'resolved_grievances': resolved,
            }
        }

        return render(request, 'collector/collector_dashboard.html', context)

    except CollectorProfile.DoesNotExist:
        messages.error(request, "Access denied. Collector profile not found.")
        return redirect('login')

#profile details


@login_required
def collector_profile_view(request):
    user = request.user  # Logged-in user (from User model)

    try:
        # Get the collector profile connected to this user
        profile = CollectorProfile.objects.get(user=user)
        collector_profile = {
                    'full_name': f"{user.first_name} {user.last_name}",
                    'email': user.email,
                    'username': user.username,
                    'district': profile.district.name,
                    'official_address': profile.official_address,
                    'collector_id': profile.collector_id,
                    'tenure_start': profile.tenure_start,
                    'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
                }

        return render(request, 'collector/profile.html', collector_profile)

    except CollectorProfile.DoesNotExist:
        messages.error(request, "Collector profile not found.")
        return redirect('dashboard')


@login_required
def officer_details(request):
    # Get collector and district
    collector_profile = get_object_or_404(CollectorProfile.objects.select_related('district'), user=request.user)
    district = collector_profile.district

    # Get HOD officers in the collector's district
    hod_officers = OfficerProfile.objects.select_related('user', 'department') \
        .filter(is_hod=True, department__district=district) \
        .only('user__first_name', 'user__last_name', 'user__email', 'user__phone', 'department__name')

    context = {
        'hod_officers': hod_officers,
        'district': district.name,
    }

    return render(request, 'collector/hod_list.html', context)


