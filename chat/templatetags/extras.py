from django import template

register = template.Library()

@register.filter(name="get")
def get(object, index):
	# return object.get
	# print("nnnnnn",object)
	return object[str(index)]