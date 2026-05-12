from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from .models import Quiz, Question, QuizResult, UserProfile


def staff_required(view_func):
    """Décorateur: accès réservé aux staff/superusers."""
    decorated = user_passes_test(
        lambda u: u.is_active and (u.is_staff or u.is_superuser),
        login_url='/login/'
    )(view_func)
    return login_required(decorated)


# ===== OVERVIEW =====
@staff_required
def admin_overview(request):
    now = timezone.now()
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)

    # Compteurs globaux
    total_users = User.objects.count()
    total_quizzes = Quiz.objects.count()
    published_quizzes = Quiz.objects.filter(is_published=True).count()
    total_plays = QuizResult.objects.count()
    total_questions = Question.objects.count()

    # Activité récente
    new_users_7d = User.objects.filter(date_joined__gte=last_7_days).count()
    new_plays_7d = QuizResult.objects.filter(played_at__gte=last_7_days).count()
    new_quizzes_7d = Quiz.objects.filter(created_at__gte=last_7_days).count()

    # Top quiz (les plus joués)
    top_quizzes = Quiz.objects.order_by('-play_count')[:5]

    # Top joueurs
    top_players = UserProfile.objects.select_related('user').order_by('-total_score')[:5]

    # Derniers utilisateurs inscrits
    recent_users = User.objects.order_by('-date_joined')[:5]

    # Dernières parties
    recent_plays = QuizResult.objects.select_related('user', 'quiz').order_by('-played_at')[:8]

    context = {
        'total_users': total_users,
        'total_quizzes': total_quizzes,
        'published_quizzes': published_quizzes,
        'unpublished_quizzes': total_quizzes - published_quizzes,
        'total_plays': total_plays,
        'total_questions': total_questions,
        'new_users_7d': new_users_7d,
        'new_plays_7d': new_plays_7d,
        'new_quizzes_7d': new_quizzes_7d,
        'top_quizzes': top_quizzes,
        'top_players': top_players,
        'recent_users': recent_users,
        'recent_plays': recent_plays,
    }
    return render(request, 'admin_panel/overview.html', context)


# ===== GESTION UTILISATEURS =====
@staff_required
def admin_users(request):
    search = request.GET.get('q', '')
    filter_status = request.GET.get('status', '')

    users = User.objects.prefetch_related('profile').order_by('-date_joined')

    if search:
        users = users.filter(username__icontains=search) | \
                users.filter(email__icontains=search)

    if filter_status == 'active':
        users = User.objects.filter(is_active=True).order_by('-date_joined')
    elif filter_status == 'inactive':
        users = User.objects.filter(is_active=False).order_by('-date_joined')
    elif filter_status == 'staff':
        users = User.objects.filter(is_staff=True).order_by('-date_joined')

    if search:
        users = users.filter(username__icontains=search)

    # Annoter avec le nombre de quiz et de parties
    users = users.annotate(
        quiz_count=Count('quizzes', distinct=True),
        play_count_total=Count('results', distinct=True),
    )

    context = {
        'users': users,
        'search': search,
        'filter_status': filter_status,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'inactive_users': User.objects.filter(is_active=False).count(),
    }
    return render(request, 'admin_panel/users.html', context)


@staff_required
def admin_user_toggle(request, user_id):
    """Activer / désactiver un utilisateur."""
    if request.method != 'POST':
        return redirect('admin_users')

    target = get_object_or_404(User, id=user_id)

    # Interdire de se désactiver soi-même
    if target == request.user:
        messages.error(request, 'Vous ne pouvez pas désactiver votre propre compte.')
        return redirect('admin_users')

    target.is_active = not target.is_active
    target.save()

    action = 'activé' if target.is_active else 'désactivé'
    messages.success(request, f'Utilisateur « {target.username} » {action}.')
    return redirect('admin_users')


@staff_required
def admin_user_make_staff(request, user_id):
    """Accorder / retirer les droits staff."""
    if request.method != 'POST':
        return redirect('admin_users')

    target = get_object_or_404(User, id=user_id)

    if target == request.user:
        messages.error(request, 'Vous ne pouvez pas modifier vos propres droits.')
        return redirect('admin_users')

    target.is_staff = not target.is_staff
    target.save()

    action = 'accordés' if target.is_staff else 'retirés'
    messages.success(request, f'Droits staff {action} pour « {target.username} ».')
    return redirect('admin_users')


@staff_required
def admin_user_delete(request, user_id):
    """Supprimer un utilisateur."""
    if request.method != 'POST':
        return redirect('admin_users')

    target = get_object_or_404(User, id=user_id)

    if target == request.user:
        messages.error(request, 'Vous ne pouvez pas supprimer votre propre compte.')
        return redirect('admin_users')

    username = target.username
    target.delete()
    messages.success(request, f'Utilisateur « {username} » supprimé.')
    return redirect('admin_users')


# ===== CRUD UTILISATEURS =====
@staff_required
def admin_user_create(request):
    """Créer un nouvel utilisateur."""
    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        email      = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        password1  = request.POST.get('password1', '')
        password2  = request.POST.get('password2', '')
        is_staff   = request.POST.get('is_staff') == 'on'
        is_active  = request.POST.get('is_active', 'on') == 'on'

        errors = {}
        if not username:
            errors['username'] = 'Le nom d\'utilisateur est requis.'
        elif User.objects.filter(username=username).exists():
            errors['username'] = 'Ce nom d\'utilisateur est déjà pris.'
        if not password1:
            errors['password1'] = 'Le mot de passe est requis.'
        elif len(password1) < 8:
            errors['password1'] = 'Le mot de passe doit contenir au moins 8 caractères.'
        elif password1 != password2:
            errors['password2'] = 'Les mots de passe ne correspondent pas.'

        if errors:
            return render(request, 'admin_panel/user_form.html', {
                'errors': errors, 'form_data': request.POST, 'action': 'Créer'
            })

        user = User.objects.create_user(
            username=username, email=email,
            password=password1,
            first_name=first_name, last_name=last_name,
        )
        user.is_staff  = is_staff
        user.is_active = is_active
        user.save()

        messages.success(request, f'Utilisateur « {username} » créé avec succès.')
        return redirect('admin_users')

    return render(request, 'admin_panel/user_form.html', {'action': 'Créer', 'form_data': {}})


@staff_required
def admin_user_edit(request, user_id):
    """Modifier un utilisateur existant."""
    target = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        email      = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        password1  = request.POST.get('password1', '')
        password2  = request.POST.get('password2', '')
        is_staff   = request.POST.get('is_staff') == 'on'
        is_active  = request.POST.get('is_active') == 'on'

        errors = {}
        if not username:
            errors['username'] = 'Le nom d\'utilisateur est requis.'
        elif User.objects.filter(username=username).exclude(id=user_id).exists():
            errors['username'] = 'Ce nom d\'utilisateur est déjà pris.'
        if password1 and len(password1) < 8:
            errors['password1'] = 'Le mot de passe doit contenir au moins 8 caractères.'
        if password1 and password1 != password2:
            errors['password2'] = 'Les mots de passe ne correspondent pas.'

        if errors:
            return render(request, 'admin_panel/user_form.html', {
                'errors': errors, 'form_data': request.POST,
                'target': target, 'action': 'Modifier'
            })

        target.username   = username
        target.email      = email
        target.first_name = first_name
        target.last_name  = last_name
        target.is_active  = is_active
        # Ne pas toucher aux droits superuser
        if not target.is_superuser:
            target.is_staff = is_staff
        if password1:
            target.set_password(password1)
        target.save()

        messages.success(request, f'Utilisateur « {username} » modifié avec succès.')
        return redirect('admin_users')

    return render(request, 'admin_panel/user_form.html', {
        'target': target, 'action': 'Modifier',
        'form_data': {
            'username': target.username, 'email': target.email,
            'first_name': target.first_name, 'last_name': target.last_name,
            'is_staff': target.is_staff, 'is_active': target.is_active,
        }
    })


# ===== GESTION QUIZ =====
@staff_required
def admin_quizzes(request):
    search = request.GET.get('q', '')
    filter_status = request.GET.get('status', '')
    filter_category = request.GET.get('category', '')

    quizzes = Quiz.objects.select_related('author').annotate(
        result_count=Count('results')
    ).order_by('-created_at')

    if search:
        quizzes = quizzes.filter(title__icontains=search)

    if filter_status == 'published':
        quizzes = quizzes.filter(is_published=True)
    elif filter_status == 'unpublished':
        quizzes = quizzes.filter(is_published=False)

    if filter_category:
        quizzes = quizzes.filter(category=filter_category)

    categories = Quiz.CATEGORY_CHOICES

    context = {
        'quizzes': quizzes,
        'search': search,
        'filter_status': filter_status,
        'filter_category': filter_category,
        'categories': categories,
        'total_quizzes': Quiz.objects.count(),
        'published_count': Quiz.objects.filter(is_published=True).count(),
        'unpublished_count': Quiz.objects.filter(is_published=False).count(),
    }
    return render(request, 'admin_panel/quizzes.html', context)


@staff_required
def admin_quiz_toggle(request, quiz_id):
    """Publier / dépublier un quiz."""
    if request.method != 'POST':
        return redirect('admin_quizzes')

    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz.is_published = not quiz.is_published
    quiz.save()

    action = 'publié' if quiz.is_published else 'dépublié'
    messages.success(request, f'Quiz « {quiz.title} » {action}.')
    return redirect('admin_quizzes')


@staff_required
def admin_quiz_delete(request, quiz_id):
    """Supprimer un quiz."""
    if request.method != 'POST':
        return redirect('admin_quizzes')

    quiz = get_object_or_404(Quiz, id=quiz_id)
    title = quiz.title
    quiz.delete()
    messages.success(request, f'Quiz « {title} » supprimé.')
    return redirect('admin_quizzes')


# ===== CRUD QUIZ =====
@staff_required
def admin_quiz_create(request):
    """Créer un nouveau quiz avec ses questions."""
    import re, json as _json

    if request.method == 'POST':
        title        = request.POST.get('title', '').strip()
        description  = request.POST.get('description', '').strip()
        category     = request.POST.get('category', '')
        difficulty   = request.POST.get('difficulty', 'medium')
        time_limit   = int(request.POST.get('time_limit', 30))
        random_order = request.POST.get('random_order') == 'on'
        is_published = request.POST.get('is_published', 'on') == 'on'
        author_id    = request.POST.get('author_id')

        errors = {}
        if not title:
            errors['title'] = 'Le titre est requis.'
        if not category:
            errors['category'] = 'La catégorie est requise.'

        if errors:
            return render(request, 'admin_panel/quiz_form.html', {
                'errors': errors, 'form_data': request.POST,
                'categories': Quiz.CATEGORY_CHOICES,
                'users': User.objects.filter(is_active=True).order_by('username'),
                'action': 'Créer',
            })

        author = request.user
        if author_id:
            try:
                author = User.objects.get(id=author_id)
            except User.DoesNotExist:
                pass

        quiz = Quiz.objects.create(
            title=title, description=description,
            category=category, difficulty=difficulty,
            time_limit=time_limit, random_order=random_order,
            is_published=is_published, author=author,
        )

        # Parser et sauvegarder les questions
        _save_questions(request.POST, quiz)

        messages.success(request, f'Quiz « {quiz.title} » créé avec succès.')
        return redirect('admin_quizzes')

    return render(request, 'admin_panel/quiz_form.html', {
        'action': 'Créer',
        'categories': Quiz.CATEGORY_CHOICES,
        'users': User.objects.filter(is_active=True).order_by('username'),
        'form_data': {'is_published': True, 'difficulty': 'medium', 'time_limit': 30},
        'existing_questions': [],
    })


@staff_required
def admin_quiz_edit(request, quiz_id):
    """Modifier un quiz existant et ses questions."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if request.method == 'POST':
        title        = request.POST.get('title', '').strip()
        description  = request.POST.get('description', '').strip()
        category     = request.POST.get('category', '')
        difficulty   = request.POST.get('difficulty', 'medium')
        time_limit   = int(request.POST.get('time_limit', 30))
        random_order = request.POST.get('random_order') == 'on'
        is_published = request.POST.get('is_published') == 'on'
        author_id    = request.POST.get('author_id')

        errors = {}
        if not title:
            errors['title'] = 'Le titre est requis.'
        if not category:
            errors['category'] = 'La catégorie est requise.'

        if errors:
            return render(request, 'admin_panel/quiz_form.html', {
                'errors': errors, 'form_data': request.POST,
                'categories': Quiz.CATEGORY_CHOICES,
                'users': User.objects.filter(is_active=True).order_by('username'),
                'quiz': quiz, 'action': 'Modifier',
                'existing_questions': list(quiz.questions.values()),
            })

        quiz.title        = title
        quiz.description  = description
        quiz.category     = category
        quiz.difficulty   = difficulty
        quiz.time_limit   = time_limit
        quiz.random_order = random_order
        quiz.is_published = is_published
        if author_id:
            try:
                quiz.author = User.objects.get(id=author_id)
            except User.DoesNotExist:
                pass
        quiz.save()

        # Supprimer les anciennes questions et recréer
        quiz.questions.all().delete()
        _save_questions(request.POST, quiz)

        messages.success(request, f'Quiz « {quiz.title} » modifié avec succès.')
        return redirect('admin_quizzes')

    import json as _json
    existing_questions = _json.dumps([q.to_json() for q in quiz.questions.all()])

    return render(request, 'admin_panel/quiz_form.html', {
        'quiz': quiz,
        'action': 'Modifier',
        'categories': Quiz.CATEGORY_CHOICES,
        'users': User.objects.filter(is_active=True).order_by('username'),
        'existing_questions': existing_questions,
        'form_data': {
            'title': quiz.title, 'description': quiz.description,
            'category': quiz.category, 'difficulty': quiz.difficulty,
            'time_limit': quiz.time_limit, 'random_order': quiz.random_order,
            'is_published': quiz.is_published, 'author_id': quiz.author_id,
        },
    })


def _save_questions(post_data, quiz):
    """Helper: parser les questions du POST et les sauvegarder."""
    import re
    questions_data = {}
    for key, value in post_data.items():
        match = re.match(r'questions\[(\d+)\]\[(\w+)\](?:\[\])?', key)
        if match:
            idx, field = match.group(1), match.group(2)
            if idx not in questions_data:
                questions_data[idx] = {'options': [], 'type': 'mcq'}
            if field == 'options':
                questions_data[idx]['options'].append(value)
            else:
                questions_data[idx][field] = value

    for i, (idx, qdata) in enumerate(sorted(questions_data.items())):
        if qdata.get('text', '').strip():
            Question.objects.create(
                quiz=quiz,
                text=qdata.get('text', ''),
                type=qdata.get('type', 'mcq'),
                correct_answer=qdata.get('correct', ''),
                options=qdata.get('options', []),
                explanation=qdata.get('explanation', ''),
                points=int(qdata.get('points', 100) or 100),
                order=i,
            )


# ===== STATISTIQUES =====
@staff_required
def admin_stats(request):
    # Stats par catégorie
    stats_by_category = Quiz.objects.values('category').annotate(
        quiz_count=Count('id'),
        total_plays=Sum('play_count'),
    ).order_by('-total_plays')

    # Stats par difficulté
    stats_by_difficulty = Quiz.objects.values('difficulty').annotate(
        quiz_count=Count('id'),
        total_plays=Sum('play_count'),
    ).order_by('-total_plays')

    # Score moyen global
    avg_score = QuizResult.objects.aggregate(avg=Avg('score'))['avg'] or 0

    # Taux de complétion (parties / utilisateurs inscrits)
    total_users = User.objects.count()
    total_plays = QuizResult.objects.count()

    # Top 10 quiz les plus joués
    top_quizzes = Quiz.objects.order_by('-play_count')[:10]

    # Activité par jour (7 derniers jours)
    daily_activity = []
    for i in range(6, -1, -1):
        day = timezone.now().date() - timedelta(days=i)
        count = QuizResult.objects.filter(played_at__date=day).count()
        daily_activity.append({
            'date': day.strftime('%d/%m'),
            'count': count,
        })

    context = {
        'stats_by_category': stats_by_category,
        'stats_by_difficulty': stats_by_difficulty,
        'avg_score': round(avg_score),
        'total_users': total_users,
        'total_plays': total_plays,
        'top_quizzes': top_quizzes,
        'daily_activity': daily_activity,
        'daily_activity_json': str([d['count'] for d in daily_activity]),
        'daily_labels_json': str([d['date'] for d in daily_activity]),
    }
    return render(request, 'admin_panel/stats.html', context)
