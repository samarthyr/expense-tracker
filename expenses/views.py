#from django.shortcuts import render

# Create your views here.
# expenses/views.py
from django.shortcuts import render, redirect
from .forms import ExpenseForm
from .models import Expense, PocketMoney
from datetime import datetime, timedelta
from django.utils.timezone import now
from django.db import models
from collections import defaultdict
from datetime import date, timedelta
import json
import csv
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    return render(request, 'expenses/add_expense.html', {'form': form})

def expense_list(request):
    # expenses = Expense.objects.all().order_by('-date')
    # total = sum(exp.amount for exp in expenses)
    # return render(request, 'expenses/expense_list.html', {'expenses': expenses, 'total': total})
    today = now().date()
    yesterday = today - timedelta(days=1)
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    start_of_month = today.replace(day=1)

    # Filter expenses
    monthly_expenses = Expense.objects.filter(date__gte=start_of_month)
    weekly_expenses = Expense.objects.filter(date__gte=start_of_week)
    monthly_total = monthly_expenses.aggregate(total=models.Sum('amount'))['total'] or 0
    weekly_total = weekly_expenses.aggregate(total=models.Sum('amount'))['total'] or 0
    today_total = Expense.objects.filter(date=today).aggregate(total=models.Sum('amount'))['total'] or 0
    yesterday_total = Expense.objects.filter(date=yesterday).aggregate(total=models.Sum('amount'))['total'] or 0
    # Pocket Money this month
    monthly_income = PocketMoney.objects.filter(date_received__gte=start_of_month).aggregate(total=models.Sum('amount'))['total'] or 0
    # Calculate remaining money
    money_left = monthly_income - monthly_total

    # # Category totals
    # category_summary = Expense.objects.values('category').annotate(total=Sum('amount'))
    # labels = [item['category'] for item in category_summary]
    # data = [float(item['total']) for item in category_summary]  # ✅ ensure it's float

    # from django.db.models import Sum

    # monthly_total = Expense.objects.filter(...).aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'monthly_expenses': monthly_expenses,
        'weekly_expenses': weekly_expenses,
        'monthly_total': monthly_total,
        'weekly_total': weekly_total,
        'today_total': today_total,
        'yesterday_total': yesterday_total,
        'monthly_income': monthly_income,
        'money_left': money_left,
        # 'category_labels': json.dumps(labels),
        # 'category_data': json.dumps(data),
    }
    return render(request, 'expenses/expense_list.html', context)

def edit_expense(request, id):
    expense = Expense.objects.get(id=id)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'expenses/edit_expense.html', {'form': form})
from django.shortcuts import get_object_or_404

def delete_expense(request, id):
    expense = get_object_or_404(Expense, id=id)
    if request.method == 'POST':
        expense.delete()
        return redirect('expense_list')
    return render(request, 'expenses/delete_expense.html', {'expense': expense})


from .models import PocketMoney
from .forms import PocketMoneyForm

def add_pocket_money(request):
    if request.method == 'POST':
        form = PocketMoneyForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('view_pocket_money')
    else:
        form = PocketMoneyForm()
    return render(request, 'expenses/add_pocket_money.html', {'form': form})

def view_pocket_money(request):
    pocket_money = PocketMoney.objects.all().order_by('-date_received')

    # Total this month
    today = now().date()
    start_of_month = today.replace(day=1)
    monthly_income = pocket_money.filter(date_received__gte=start_of_month).aggregate(total=models.Sum('amount'))['total'] or 0

    return render(request, 'expenses/view_pocket_money.html', {
        'pocket_money': pocket_money,
        'monthly_income': monthly_income
    })
def edit_pocket_money(request, id):
    pocket_money = PocketMoney.objects.get(id=id)
    if request.method == 'POST':
        form = PocketMoneyForm(request.POST, instance=pocket_money)
        if form.is_valid():
            form.save()
            return redirect('view_pocket_money')
    else:
        form = PocketMoneyForm(instance=pocket_money)
    return render(request, 'expenses/edit_pocket_money.html', {'form': form})



def weekly_expenses(request):
    from django.db.models import Q, Avg, Max, Min, Sum
    from django.db.models.functions import ExtractYear, ExtractWeek
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    # Get filter params
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category = request.GET.get('category')
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    selected_year = request.GET.get('year')
    selected_week = request.GET.get('week')

    # Get all available years and weeks from expenses
    all_years = Expense.objects.annotate(year=ExtractYear('date')).values_list('year', flat=True).distinct().order_by('-year')
    all_weeks = Expense.objects.annotate(week=ExtractWeek('date')).values_list('week', flat=True).distinct().order_by('week')

    # Start with all expenses
    expenses = Expense.objects.all().order_by('-date')
    if start_date:
        expenses = expenses.filter(date__gte=start_date)
    if end_date:
        expenses = expenses.filter(date__lte=end_date)
    if category:
        expenses = expenses.filter(category=category)
    if min_amount:
        expenses = expenses.filter(amount__gte=min_amount)
    if max_amount:
        expenses = expenses.filter(amount__lte=max_amount)
    if selected_year:
        expenses = expenses.filter(date__year=selected_year)
    if selected_week:
        expenses = expenses.filter(date__week=selected_week)

    # Group by day name
    weekly_grouped = defaultdict(list)
    for expense in expenses.order_by('date'):
        day = expense.date.strftime('%A')
        weekly_grouped[day].append(expense)

    # Get all unique categories for the filter dropdown
    categories = Expense.objects.values_list('category', flat=True).distinct()

    # Calculate total for the filtered week
    week_total = expenses.aggregate(total=models.Sum('amount'))['total'] or 0
    
    # Calculate summary info
    expense_count = expenses.count()
    average_amount = expenses.aggregate(avg=Avg('amount'))['avg'] or 0
    max_amount_val = expenses.aggregate(max=Max('amount'))['max'] or 0
    min_amount_val = expenses.aggregate(min=Min('amount'))['min'] or 0
    # Find the category with the highest total spending
    category_totals = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    if category_totals:
        top_category = category_totals[0]['category']
        top_category_amount = category_totals[0]['total']
    else:
        top_category = None
        top_category_amount = 0

    return render(request, 'expenses/weekly_expenses.html', {
        'weekly_grouped': dict(weekly_grouped),
        'categories': categories,
        'week_total': week_total,
        'expense_count': expense_count,
        'average_amount': average_amount,
        'max_amount': max_amount_val,
        'min_amount': min_amount_val,
        'top_category': top_category,
        'top_category_amount': top_category_amount,
        'all_years': all_years,
        'all_weeks': all_weeks,
        'selected_year': selected_year,
        'selected_week': selected_week,
    })


def monthly_expenses(request):
    from django.db.models import Avg, Max, Min
    from django.db.models.functions import ExtractYear, ExtractMonth
    monthly_grouped = defaultdict(list)
    # Get filter params
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category = request.GET.get('category')
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')

    # Get all available years and months from expenses
    all_years = Expense.objects.annotate(year=ExtractYear('date')).values_list('year', flat=True).distinct().order_by('-year')
    all_months = [
        (i, datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)
    ]

    # Start with all expenses
    expenses = Expense.objects.all().order_by('-date')
    if start_date:
        expenses = expenses.filter(date__gte=start_date)
    if end_date:
        expenses = expenses.filter(date__lte=end_date)
    if category:
        expenses = expenses.filter(category=category)
    if min_amount:
        expenses = expenses.filter(amount__gte=min_amount)
    if max_amount:
        expenses = expenses.filter(amount__lte=max_amount)
    if selected_year:
        expenses = expenses.filter(date__year=selected_year)
    if selected_month:
        expenses = expenses.filter(date__month=selected_month)

    for exp in expenses:
        month = exp.date.strftime('%B %Y')
        monthly_grouped[month].append(exp)

    # Calculate summary info
    month_total = expenses.aggregate(total=models.Sum('amount'))['total'] or 0
    expense_count = expenses.count()
    average_amount = expenses.aggregate(avg=Avg('amount'))['avg'] or 0
    max_amount_val = expenses.aggregate(max=Max('amount'))['max'] or 0
    min_amount_val = expenses.aggregate(min=Min('amount'))['min'] or 0
    categories = Expense.objects.values_list('category', flat=True).distinct()

    # Find the category with the highest total spending
    from django.db.models import Sum
    category_totals = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    if category_totals:
        top_category = category_totals[0]['category']
        top_category_amount = category_totals[0]['total']
    else:
        top_category = None
        top_category_amount = 0

    return render(request, 'expenses/monthly_expenses.html', {
        'monthly_grouped': dict(monthly_grouped),
        'month_total': month_total,
        'expense_count': expense_count,
        'average_amount': average_amount,
        'max_amount': max_amount_val,
        'min_amount': min_amount_val,
        'categories': categories,
        'top_category': top_category,
        'top_category_amount': top_category_amount,
        'all_years': all_years,
        'all_months': all_months,
        'selected_year': selected_year,
        'selected_month': selected_month,
    })

from django.shortcuts import render
from .models import Expense
from django.db.models import Sum
from collections import defaultdict

def monthly_overview(request):
    # Aggregate total expenses by month and year
    monthly_summary = (
        Expense.objects
        .values('month', 'year')
        .annotate(total=Sum('amount'))
        .order_by('-year', '-month')
    )

    return render(request, 'expenses/monthly_overview.html', {
        'monthly_summary': monthly_summary
    })


def monthly_detail(request, year, month):
    expenses = Expense.objects.filter(month=month, year=year).order_by('-date')

    total = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    return render(request, 'expenses/monthly_detail.html', {
        'expenses': expenses,
        'month': month,
        'year': year,
        'total': total
    })


def download_monthly_expenses(request):
    # Use the same filtering logic as before
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category = request.GET.get('category')
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')

    expenses = Expense.objects.all().order_by('-date')
    if start_date:
        expenses = expenses.filter(date__gte=start_date)
    if end_date:
        expenses = expenses.filter(date__lte=end_date)
    if category:
        expenses = expenses.filter(category=category)
    if min_amount:
        expenses = expenses.filter(amount__gte=min_amount)
    if max_amount:
        expenses = expenses.filter(amount__lte=max_amount)
    if selected_year and selected_year != "None":
        expenses = expenses.filter(date__year=selected_year)
    if selected_month and selected_month != "None":
        expenses = expenses.filter(date__month=selected_month)

    # Calculate totals by category
    from django.db.models import Sum
    category_totals = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    overall_total = sum(cat['total'] for cat in category_totals)

    # Determine month and year label for the report
    import calendar
    if selected_month and selected_month != "None":
        try:
            month_label = calendar.month_name[int(selected_month)]
        except Exception:
            month_label = str(selected_month)
    else:
        month_label = None
    if selected_year and selected_year != "None":
        year_label = str(selected_year)
    else:
        year_label = None
    if month_label and year_label:
        period_label = f"{month_label} {year_label}"
    elif month_label:
        period_label = month_label
    elif year_label:
        period_label = year_label
    else:
        period_label = ""

    # Create the HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="monthly_expenses.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Monthly Expenses Report")
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 70, f"Period: {period_label}")

    # Show overall total at the top
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 100, f"Total Amount: Rs. {overall_total:.2f}")

    # Table headers for category summary
    p.setFont("Helvetica-Bold", 12)
    y = height - 140
    p.drawString(50, y, "Category")
    p.drawString(250, y, "Total Amount")

    # Table rows for each category
    p.setFont("Helvetica", 11)
    y -= 20
    for cat in category_totals:
        if y < 50:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y, "Category")
            p.drawString(250, y, "Total Amount")
            p.setFont("Helvetica", 11)
            y -= 20
        p.drawString(50, y, cat['category'])
        p.drawString(250, y, f"Rs. {cat['total']:.2f}")
        y -= 18

    p.showPage()
    p.save()
    return response

