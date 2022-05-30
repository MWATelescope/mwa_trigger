from urllib.parse import urlencode
from collections import OrderedDict

from django import template
from django.utils.safestring import mark_safe
from django.conf import settings

register = template.Library()

@register.simple_tag
def url_switch(request, field, pair=['deg', 'arcmin']):
    # Modified https://stackoverflow.com/questions/2272370/sortable-table-columns-in-django
    dict_ = request.GET.copy()

    if field == 'poserr_unit' and field in dict_.keys():
        # Switch to other value
        if dict_[field] == pair[0]:
            dict_[field] = pair[1]
        elif dict_[field] == pair[1]:
            dict_[field] = pair[0]
    else:
        # Nothing set so use deg as default
        dict_[field] = pair[0]

    return urlencode(OrderedDict(sorted(dict_.items())))


@register.simple_tag()
def multiply(qty, multiply_by, decimal_places, *args, **kwargs):
    # Modified https://stackoverflow.com/questions/19588160/multiply-in-django-template
    # you would need to do any localization of the result here
    return round(qty * multiply_by, decimal_places)

@register.simple_tag()
def help_wrap(title, *args, **kwargs):
    # Will wrap the input with the html to make a nice hover over help question mark
    return mark_safe(f'<span data-toggle=\'tooltip\' title=\'{title}\'><img width="25" height="25" src="{settings.STATIC_URL}trigger_app/question_mark.png" alt="?"/></span>')

@register.filter
def index(indexable, i):
    return indexable[i]