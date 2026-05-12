from django import template

register = template.Library()


@register.filter
def difficulty_class(value):
    """Retourne la classe CSS Bootstrap selon la difficulté."""
    classes = {
        'easy': 'badge-green',
        'medium': 'badge-yellow',
        'hard': 'badge-red',
    }
    return classes.get(value, 'badge-blue')


@register.filter
def difficulty_label(value):
    """Retourne le label lisible selon la difficulté."""
    labels = {
        'easy': 'Facile',
        'medium': 'Moyen',
        'hard': 'Difficile',
    }
    return labels.get(value, value)
