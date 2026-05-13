from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Avg, Q
import json
import random

from .models import Quiz, Question, QuizResult, UserProfile


# ===== HOME =====
def home(request):
    popular_quizzes = Quiz.objects.filter(is_published=True).order_by('-play_count')[:6]
    top_players = UserProfile.objects.select_related('user').order_by('-total_score')[:5].annotate(
        quiz_count=Count('user__results')
    )

    context = {
        'popular_quizzes': popular_quizzes,
        'top_players': top_players,
        'total_quizzes': Quiz.objects.filter(is_published=True).count(),
        'total_users': UserProfile.objects.count(),
        'total_plays': QuizResult.objects.count(),
    }
    return render(request, 'quiz/home.html', context)


# ===== QUIZ LIST =====
def quiz_list(request):
    quizzes = Quiz.objects.filter(is_published=True).select_related('author')

    q = request.GET.get('q', '')
    category = request.GET.get('category', '')
    difficulty = request.GET.get('difficulty', '')
    sort = request.GET.get('sort', 'popular')

    if q:
        quizzes = quizzes.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if category:
        quizzes = quizzes.filter(category=category)
    if difficulty:
        quizzes = quizzes.filter(difficulty=difficulty)

    if sort == 'newest':
        quizzes = quizzes.order_by('-created_at')
    elif sort == 'rating':
        quizzes = quizzes.annotate(avg=Avg('results__score')).order_by('-avg')
    else:
        quizzes = quizzes.order_by('-play_count')

    paginator = Paginator(quizzes, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    categories = Quiz.CATEGORY_CHOICES

    return render(request, 'quiz/quiz_list.html', {
        'quizzes': page_obj,
        'page_obj': page_obj,
        'categories': [c[0] for c in categories],
    })


# ===== QUIZ DETAIL =====
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_published=True)

    top_scores = QuizResult.objects.filter(
        quiz=quiz, user__isnull=False
    ).select_related('user').order_by('-score')[:5]

    my_best = None
    if request.user.is_authenticated:
        my_best = QuizResult.objects.filter(
            quiz=quiz, user=request.user
        ).order_by('-score').first()

    return render(request, 'quiz/quiz_detail.html', {
        'quiz': quiz,
        'top_scores': top_scores,
        'my_best': my_best,
    })


# ===== QUIZ PLAY =====
def quiz_play(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_published=True)
    questions = list(quiz.questions.all())

    if quiz.random_order:
        random.shuffle(questions)

    quiz_json = json.dumps([q.to_json() for q in questions])
    return render(request, 'quiz/quiz_play.html', {
        'quiz': quiz,
        'quiz_json': quiz_json,
        'total_questions': len(questions),
    })


# ===== SAVE SCORE =====
def save_score(request, quiz_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    quiz = get_object_or_404(Quiz, id=quiz_id)
    data = json.loads(request.body)

    result = QuizResult.objects.create(
        quiz=quiz,
        user=request.user if request.user.is_authenticated else None,
        score=data.get('score', 0),
        correct=data.get('correct', 0),
        wrong=data.get('wrong', 0),
        time_bonus=data.get('time_bonus', 0),
    )

    quiz.play_count += 1
    quiz.save(update_fields=['play_count'])

    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.update_stats(result)

    return JsonResponse({'status': 'ok', 'score': result.score})


# ===== CREATE QUIZ =====
@login_required
def quiz_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '')
        difficulty = request.POST.get('difficulty', 'medium')
        time_limit = int(request.POST.get('time_limit', 30))
        random_order = request.POST.get('random_order', 'false') == 'true'

        if not title or not category:
            messages.error(request, 'Veuillez remplir tous les champs obligatoires.')
            return redirect('quiz_create')

        quiz = Quiz.objects.create(
            title=title,
            description=description,
            category=category,
            difficulty=difficulty,
            time_limit=time_limit,
            random_order=random_order,
            author=request.user,
        )

        # Parse questions
        import re
        questions_data = {}
        for key, values in request.POST.lists():
            if key.startswith('questions['):
                match = re.match(r'questions\[(\d+)\]\[(\w+)\](?:\[\])?', key)
                if match:
                    idx, field = match.group(1), match.group(2)
                    if idx not in questions_data:
                        questions_data[idx] = {'options': [], 'type': 'mcq'}
                    if field == 'options':
                        questions_data[idx]['options'].extend(values)
                    else:
                        questions_data[idx][field] = values[-1]

        for i, (idx, qdata) in enumerate(sorted(questions_data.items())):
            if qdata.get('text'):
                Question.objects.create(
                    quiz=quiz,
                    text=qdata.get('text', ''),
                    type=qdata.get('type', 'mcq'),
                    correct_answer=qdata.get('correct', ''),
                    options=qdata.get('options', []),
                    explanation=qdata.get('explanation', ''),
                    points=int(qdata.get('points', 100)),
                    order=i,
                )

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.quizzes_created += 1
        profile.save()
        profile.check_badges()

        messages.success(request, f'Quiz "{quiz.title}" créé avec succès !')
        return redirect('quiz_list')

    return render(request, 'quiz/quiz_create.html', {
        'categories': Quiz.CATEGORY_CHOICES,
        'action': 'Créer',
        'form': {},
    })


# ===== EDIT QUIZ =====
@login_required
def quiz_edit(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, author=request.user)
    if request.method == 'POST':
        quiz.title = request.POST.get('title', quiz.title)
        quiz.description = request.POST.get('description', quiz.description)
        quiz.category = request.POST.get('category', quiz.category)
        quiz.difficulty = request.POST.get('difficulty', quiz.difficulty)
        quiz.time_limit = int(request.POST.get('time_limit', quiz.time_limit))
        quiz.random_order = request.POST.get('random_order', 'false') == 'true'
        quiz.save()

        # Supprimer les anciennes questions et recréer depuis le formulaire
        quiz.questions.all().delete()
        import re
        questions_data = {}
        for key, values in request.POST.lists():
            if key.startswith('questions['):
                match = re.match(r'questions\[(\d+)\]\[(\w+)\](?:\[\])?', key)
                if match:
                    idx, field = match.group(1), match.group(2)
                    if idx not in questions_data:
                        questions_data[idx] = {'options': [], 'type': 'mcq'}
                    if field == 'options':
                        questions_data[idx]['options'].extend(values)
                    else:
                        questions_data[idx][field] = values[-1]

        from .models import Question
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

        messages.success(request, f'Quiz "{quiz.title}" mis à jour !')
        return redirect('quiz_list')

    existing_questions = json.dumps([q.to_json() for q in quiz.questions.all()])
    return render(request, 'quiz/quiz_create.html', {
        'quiz': quiz,
        'existing_questions': existing_questions,
        'categories': Quiz.CATEGORY_CHOICES,
        'action': 'Modifier',
    })


# ===== LEADERBOARD =====
def leaderboard(request):
    leaderboard_data = UserProfile.objects.select_related('user').order_by('-total_score').annotate(
        quiz_count=Count('user__results')
    )[:50]

    return render(request, 'quiz/leaderboard.html', {'leaderboard': leaderboard_data})


# ===== PROFILE =====
@login_required
def profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    history = QuizResult.objects.filter(user=request.user).select_related('quiz').order_by('-played_at')[:20]
    my_quizzes = Quiz.objects.filter(author=request.user).order_by('-created_at')

    stats = {
        'total_score': profile.total_score,
        'quizzes_played': profile.quizzes_played,
        'quizzes_created': my_quizzes.count(),
        'best_score': profile.best_score,
    }

    return render(request, 'quiz/profile.html', {
        'stats': stats,
        'history': history,
        'my_quizzes': my_quizzes,
        'badges': profile.get_badges_display(),
    })


# ===== REJOINDRE PAR CODE PIN =====
def quiz_join(request):
    """Page d'accueil pour entrer un code PIN et rejoindre un quiz."""
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().replace(' ', '')
        if not code:
            return render(request, 'quiz_join.html', {'error': 'Entrez un code PIN.'})
        try:
            quiz = Quiz.objects.get(access_code=code, is_published=True)
            return redirect('quiz_play', quiz_id=quiz.id)
        except Quiz.DoesNotExist:
            return render(request, 'quiz_join.html', {
                'error': f'Code « {code} » invalide ou quiz non disponible.',
                'code': code,
            })
    return render(request, 'quiz_join.html', {})


def quiz_join_direct(request, code):
    """Accès direct via lien partagé : /join/XXXXXX/"""
    try:
        quiz = Quiz.objects.get(access_code=code, is_published=True)
        return redirect('quiz_play', quiz_id=quiz.id)
    except Quiz.DoesNotExist:
        return render(request, 'quiz_join.html', {
            'error': f'Ce lien est invalide ou le quiz n\'est plus disponible.',
        })


# ===== AUTH =====
def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        form.data = form.data.copy()
        # Add email support
        from django.contrib.auth.models import User
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')

        errors = {}
        if User.objects.filter(username=username).exists():
            errors['username'] = 'Ce nom d\'utilisateur est déjà pris.'
        if password1 != password2:
            errors['password2'] = 'Les mots de passe ne correspondent pas.'
        if len(password1 or '') < 8:
            errors['password1'] = 'Le mot de passe doit contenir au moins 8 caractères.'

        if not errors:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
            )
            login(request, user)
            messages.success(request, f'Bienvenue {username} ! Votre compte a été créé.')
            return redirect('home')

        return render(request, 'register.html', {'form': {'errors': errors}})

    return render(request, 'register.html', {'form': {}})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'home'))
        return render(request, 'login.html', {'form': {'errors': True}})

    return render(request, 'login.html', {'form': {}})


def logout_view(request):
    logout(request)
    messages.success(request, 'Vous êtes déconnecté.')
    return redirect('home')
