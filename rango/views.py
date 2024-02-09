from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.urls import reverse
from rango.forms import PageForm, CategoryForm, UserForm, UserProfileForm, LoginForm
from rango.models import Category, Page
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from datetime import datetime
from django.db.utils import IntegrityError

def index(request):
    category_list = Category.objects.order_by('-likes')[:5]
    page_list = Page.objects.order_by('-views')[:5]
    context_dict = {}
    context_dict['boldmessage'] = 'Crunchy, creamy, cookie, candy, cupcake!'
    context_dict['categories'] = category_list
    context_dict['pages'] = page_list

    
    # Update last visit time
    if 'last_visit' in request.session:
        last_visit = datetime.strptime(request.session['last_visit'], '%Y-%m-%d %H:%M:%S.%f')
        visits = request.session.get('visits', 0)
    else:
        # First visit, initialize last_visit and visits
        last_visit = None  # Provide a default value
        visits = 0

    # Check if last_visit is not None to avoid UnboundLocalError
    if last_visit is not None and (datetime.now() - last_visit).days > 0:
        request.session['visits'] = visits + 1
        request.session['last_visit'] = str(datetime.now())



    # Call the helper function to handle the cookies
    visitor_cookie_handler(request)

    # Get visits from the session
    # Get visits from the session
    visits = request.session['visits']

    response = render(request, 'rango/index.html', context=context_dict)
    return response


def about(request):
    # Call the helper function to handle the cookies
    visitor_cookie_handler(request)

    # Get all categories for the context
    categories = Category.objects.all()

    # Get the number of visits from the session
    visits = request.session['visits']

    # Define your name
    your_name = '2790363l'

    context = {
        'categories': categories,
        'your_name': your_name,
        'visits': visits, 
    }

    return render(request, 'rango/about.html', context=context)

@login_required
def add_category(request):
    form = CategoryForm()

    # A HTTP POST?
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        # Have we been provided with a valid form?
        if form.is_valid():
            try:
                form.save(commit=True)
                return redirect('rango:index')
            except IntegrityError:
                # Handle the case where the category with the same name already exists
                form.add_error('name', 'Category with this name already exists.')

    else:
        # The supplied form contained errors -
        # just print them to the terminal.
        print(form.errors)

    # Will handle the bad form, new form, or no form supplied cases.
    # Render the form with error messages (if any).
    return render(request, 'rango/add_category.html', {'form': form})

def show_category(request, category_name_slug):
    # Create a context dictionary which we can pass
    # to the template rendering engine.
    context_dict = {}

    try:
        # Can we find a category name slug with the given name?
        # If we can't, the .get() method raises a DoesNotExist exception.
        # The .get() method returns one model instance or raises an exception.
        category = Category.objects.get(slug=category_name_slug)

        # Retrieve all of the associated pages.
        # The filter() will return a list of page objects or an empty list.
        pages = Page.objects.filter(category=category)

        # Adds our results list to the template context under name pages.
        context_dict['pages'] = pages

        # We also add the category object from
        # the database to the context dictionary.
        # We'll use this in the template to verify that the category exists.
        context_dict['category'] = category
    except Category.DoesNotExist:
        # We get here if we didn't find the specified category.
        # Don't do anything -
        # the template will display the "no category" message for us.
        context_dict['category'] = None
        context_dict['pages'] = None

    # Go render the response and return it to the client.
    return render(request, 'rango/category.html', context_dict)

@login_required
def add_page(request, category_name_slug):
    try:
        category = Category.objects.get(slug=category_name_slug)
    except Category.DoesNotExist:
        category = None

    # You cannot add a page to a Category that does not exist...
    if category is None:
        return redirect('rango:index')

    form = PageForm()

    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            if category:
                page = form.save(commit=False)
                page.category = category
                page.views = 0
                page.save()

                page.views += 1  # This line should be part of the if block

        return redirect(reverse('rango:show_category', kwargs={'category_name_slug': category_name_slug}))

    else:
        print(form.errors)

    context_dict = {'form': form, 'category': category}
    return render(request, 'rango/add_page.html', context=context_dict)

def register(request):
    # A boolean value for telling the template
    # whether the registration was successful.
    # Set to False initially. Code changes value to
    # True when registration succeeds.
    registered = False

    # If it's an HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        user_form = UserForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        # If the two forms are valid...
        if user_form.is_valid() and profile_form.is_valid():
            # Save the user's form data to the database.
            user = user_form.save()

            # Now we hash the password with the set_password method.
            # Once hashed, we can update the user object.
            user.set_password(user.password)
            user.save()

            # Now sort out the UserProfile instance.
            # Since we need to set the user attribute ourselves,
            # we set commit=False. This delays saving the model
            # until we're ready to avoid integrity problems.
            profile = profile_form.save(commit=False)
            profile.user = user

            # Did the user provide a profile picture?
            # If so, we need to get it from the input form and
            # put it in the UserProfile model.
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            # Now we save the UserProfile model instance.
            profile.save()

            # Update our variable to indicate that the template
            # registration was successful.
            registered = True
        else:
            # Invalid form or forms - mistakes or something else?
            # Print problems to the terminal.
            print(user_form.errors, profile_form.errors)
    else:
        # Not an HTTP POST, so we render our form using two ModelForm instances.
        # These forms will be blank, ready for user input.
        user_form = UserForm()
        profile_form = UserProfileForm()

    # Render the template depending on the context.
    return render(request, 'rango/register.html', context={'user_form': user_form, 'profile_form': profile_form, 'registered': registered})

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user:
                if user.is_active:
                    login(request, user)
                    return redirect('rango:index')
                else:
                    return HttpResponse("Your Rango account is disabled.")
            else:
                return HttpResponse("Invalid login details supplied.")
    else:
        form = LoginForm()

    return render(request, 'rango/login.html', {'form': form})

@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)
    # Take the user back to the homepage.
    return redirect(reverse('rango:index'))

def restricted(request):
    # Your view logic here
    return render(request, 'rango/restricted.html')  # Replace with your actual template

def visitor_cookie_handler(request):
    # Get the number of visits to the site.
    visits = int(request.session.get('visits', '1'))

    # Get the last visit time from the 'last_visit' cookie.
    last_visit_cookie = request.COOKIES.get('last_visit', str(datetime.now()))
    last_visit_time = datetime.strptime(last_visit_cookie[:-7], '%Y-%m-%d %H:%M:%S')

    # If it's been more than a day since the last visit...
    if (datetime.now() - last_visit_time).days > 0:
        visits = visits + 1
        # Update the last visit cookie now that we have updated the count.
        response = HttpResponse()
        response.set_cookie('last_visit', str(datetime.now()))
    else:
        # Set the last visit cookie.
        response = HttpResponse()
        response.set_cookie('last_visit', last_visit_cookie)

    # Update/set the 'visits' in the session.
    request.session['visits'] = visits

    return response
