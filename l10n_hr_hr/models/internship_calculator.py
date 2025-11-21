"""
Class used for internship calculation based on:
    - contract length(date_start and date_end),
    - used_in_internship_calculation flag
    - internship type (internship with increased duration(0 - 4))
"""
import datetime
from dateutil.relativedelta import relativedelta


def calculate_internship(records):
    overall_days, overall_months, overall_years = 0, 0, 0

    if len(records) != 0:
        # remove records with overlapping dates and non-internship parameters
        data = prepare_data(records)

        for parameter in data:
            date_start = parameter[0]
            date_end = parameter[1]
            internship_type = parameter[3]
            coef = parameter[4]

            # if parameter hasn't started yet then don't calculate it
            if date_start < datetime.date.today():
                # if there is no end_date in parameter or end date is after current date then current date is end_date
                if date_end is False or date_end > datetime.date.today():
                    date_end = datetime.date.today()

                # calculate internship from parameter date
                date_diff = relativedelta(date_end, date_start)
                days = (date_end - date_start).days * coef

                months = ((date_diff.years * 12)) * coef + date_diff.months * coef
                current_parameter_years = months // 12
                current_parameter_months = months % 12
                current_parameter_days = (date_diff.days) * coef + (months - int(months)) * 30
                # current_parameter_days, current_parameter_months, current_parameter_years\
                #     = date_diff.days + 1, date_diff.months, date_diff.years

                # if internship is with increased duration then calculate it
                if internship_type != '0':
                    current_parameter_days, current_parameter_months, current_parameter_years = \
                        calculate_internship_with_increased_duration(internship_type,
                                                                     current_parameter_days,
                                                                     current_parameter_months,
                                                                     current_parameter_years)

                # add current parameter internship to overall internship
                overall_days += int(current_parameter_days)
                overall_months += int(current_parameter_months)
                overall_years += int(current_parameter_years)

    return divide_internship_results(overall_days, overall_months, overall_years)

# function for getting items for sorting by start date(older dates first)
def get_key(item):
    return item[0]

# clear records with overlapping dates, they do not come into internship account
def prepare_data(records):
    data = []
    i = 0

    # taking data that will be used in internship calculation
    for param in records.salary_parameters_ids:
        regular_day_work_hours = param.contract_id.resource_calendar_id.hours_per_day
        param_coef = ((param.day_hours or 8) / regular_day_work_hours) or 1
        data.append([param.date_from, param.date_to, param.contract_id.area_type.used_in_internship_calculation, param.contract_id.internship_type, param_coef])

    data = sorted(data, key=get_key)
    length = len(data)

    while i < length:
        # check flag used_in_internship_calculation, if it is False then it is not eligible for internship calculation
        if data[i][2]:  # used_in_internship_calculation flag
            j = i + 1

            while j < length:
                if data[j][2]:  # flag used_in_internship_calculation
                    date_end_i = data[i][1]
                    internship_type_i = int(data[i][3])
                    date_start_j = data[j][0]
                    date_end_j = data[j][1]
                    internship_type_j = int(data[j][3])

                    if date_end_i is False:  # whole parameter duration is in other parameter range
                        if internship_type_j > internship_type_i:
                            new_entry = [date_end_j + datetime.timedelta(days=1), data[i][1], data[i][2], data[i][3]]
                            data[i][1] = date_start_j - datetime.timedelta(days=1)
                            data.insert(j+1, new_entry)
                            j += 1
                            length += 1
                        else:
                            del data[j]
                            length -= 1
                    else:
                        if date_end_i >= date_start_j:
                            if date_end_j is False or date_end_j >= date_end_i:
                                if internship_type_j > internship_type_i:
                                    data[i][1] = date_start_j - datetime.timedelta(days=1)
                                    j += 1
                                else:
                                    data[j][0] = date_end_i + datetime.timedelta(days=1)
                                    j += 1
                            elif date_end_i > date_end_j:  # whole parameter duration is in other parameter range
                                if internship_type_j > internship_type_i:
                                    new_entry = [date_end_j + datetime.timedelta(days=1), data[i][1], data[i][2],
                                                 data[i][3]]
                                    data[i][1] = date_start_j - datetime.timedelta(days=1)
                                    data.insert(j+1, new_entry)
                                    j += 1
                                    length += 1
                                else:
                                    del data[j]
                                    length -= 1
                        else:
                            j += 1
                else:
                    del data[j]
                    length -= 1
        else:
            del data[i]
            length -= 1
            i -= 1

        i += 1
    return data

def calculate_internship_with_increased_duration(internship_type, days, months, years):
    years_added, months_added, days_added = 0, 0, 0

    if internship_type == '1':
        years_added = years / 6
        months_added = (months + 12 * (years % 6)) / 6
        days_added = (days + 30 * ((months + 12 * (years % 6)) % 6)) / 6
    elif internship_type == '2':
        years_added = years / 4
        months_added = (months + 12 * (years % 4)) / 4
        days_added = (days + 30 * ((months + 12 * (years % 4)) % 4)) / 4
    elif internship_type == '3':
        years_added = years / 3
        months_added = (months + 12 * (years % 3)) / 3
        days_added = (days + 30 * ((months + 12 * (years % 3)) % 3)) / 3
    elif internship_type == '4':
        years_added = years / 2
        months_added = (months + 12 * (years % 2)) / 2
        days_added = (days + 30 * ((months + 12 * (years % 2)) % 2)) / 2

    years += years_added
    months += months_added
    days += days_added

    return divide_internship_results(days, months, years)

# When days > 30 or months > 12 this method divides values so that corresponds with actual date values
def divide_internship_results(days, months, years):
    if days >= 30:
        months += days / 30
        days = days % 30

    if months >= 12:
        years += months / 12
        months = months % 12

    return days, months, years

# check if there are multiple same dates for work experience calculation
def check_contracts_for_internship(records, new_start_date, new_end_date):
    for rec in records:
        if not rec.area_type.used_in_internship_calculation:
            continue

        if new_end_date is False:
            if rec.date_end is False:
                return True
            elif new_start_date <= rec.date_end:
                return True
        else:
            if rec.date_end is False:
                if rec.date_start <= new_end_date:
                    return True
            else:  # RANGE
                if rec.date_start <= new_start_date <= rec.date_end:
                    return True
                elif new_start_date <= rec.date_start <= new_end_date:
                    return True

    return False
