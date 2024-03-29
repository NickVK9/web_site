from django import template
import locale


locale.setlocale(locale.LC_ALL,'en_CA.UTF-8')


register = template.Library()


@register.filter()
def currency(value):
	try:
		value = float(str(value))
	except:
		return value

	return locale.currency(value, grouping=True)
