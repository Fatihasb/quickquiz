from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json
import random
import string


class Quiz(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Facile'),
        ('medium', 'Moyen'),
        ('hard', 'Difficile'),
    ]

    CATEGORY_CHOICES = [
        ('Sciences', 'Sciences'),
        ('Histoire', 'Histoire'),
        ('Géographie', 'Géographie'),
        ('Sport', 'Sport'),
        ('Culture', 'Culture générale'),
        ('Technologie', 'Technologie'),
        ('Musique', 'Musique'),
        ('Cinéma', 'Cinéma'),
        ('Littérature', 'Littérature'),
        ('Mathématiques', 'Mathématiques'),
        ('Langues', 'Langues'),
        ('Autre', 'Autre'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    time_limit = models.IntegerField(default=30, help_text="Secondes par question")
    random_order = models.BooleanField(default=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quizzes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)
    play_count = models.IntegerField(default=0)
    access_code = models.CharField(max_length=8, unique=True, blank=True, help_text="Code PIN d'accès au quiz")

    class Meta:
        ordering = ['-play_count', '-created_at']

    def __str__(self):
        return self.title

    @staticmethod
    def generate_access_code():
        """Génère un code PIN unique à 6 chiffres."""
        while True:
            code = ''.join(random.choices(string.digits, k=6))
            if not Quiz.objects.filter(access_code=code).exists():
                return code

    def save(self, *args, **kwargs):
        if not self.access_code:
            self.access_code = Quiz.generate_access_code()
        super().save(*args, **kwargs)

    def get_join_url(self):
        return f"/join/{self.access_code}/"

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def avg_score(self):
        results = self.results.all()
        if not results:
            return None
        return round(results.aggregate(models.Avg('score'))['score__avg'] or 0)


class Question(models.Model):
    TYPE_CHOICES = [
        ('mcq', 'QCM'),
        ('truefalse', 'Vrai/Faux'),
        ('short', 'Réponse courte'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='mcq')
    correct_answer = models.CharField(max_length=500)
    options = models.JSONField(default=list, blank=True)
    accepted_answers = models.JSONField(default=list, blank=True)
    explanation = models.TextField(blank=True)
    points = models.IntegerField(default=100)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.text[:50]}"

    def to_json(self):
        return {
            'id': self.id,
            'text': self.text,
            'type': self.type,
            'options': self.options,
            'correct_answer': self.correct_answer,
            'accepted_answers': self.accepted_answers,
            'explanation': self.explanation,
            'points': self.points,
        }


class QuizResult(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='results')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='results', null=True, blank=True)
    score = models.IntegerField(default=0)
    correct = models.IntegerField(default=0)
    wrong = models.IntegerField(default=0)
    time_bonus = models.IntegerField(default=0)
    played_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-played_at']

    def __str__(self):
        return f"{self.user} - {self.quiz} - {self.score}pts"


class UserProfile(models.Model):
    BADGE_LIST = [
        {'id': 'first_quiz', 'name': 'Premier Quiz', 'icon': '🎯', 'condition': 'quizzes_played >= 1'},
        {'id': 'quiz_master', 'name': 'Quiz Master', 'icon': '🏆', 'condition': 'quizzes_played >= 10'},
        {'id': 'creator', 'name': 'Créateur', 'icon': '✏️', 'condition': 'quizzes_created >= 1'},
        {'id': 'perfect', 'name': 'Parfait', 'icon': '⭐', 'condition': 'has_perfect_score'},
        {'id': 'speedster', 'name': 'Rapide', 'icon': '⚡', 'condition': 'time_bonus >= 500'},
        {'id': 'scholar', 'name': 'Érudit', 'icon': '📚', 'condition': 'total_score >= 1000'},
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    total_score = models.IntegerField(default=0)
    quizzes_played = models.IntegerField(default=0)
    quizzes_created = models.IntegerField(default=0)
    best_score = models.IntegerField(default=0)
    badges_earned = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile: {self.user.username}"

    def update_stats(self, result):
        self.total_score += result.score
        self.quizzes_played += 1
        if result.score > self.best_score:
            self.best_score = result.score
        self.save()
        self.check_badges()

    def check_badges(self):
        for badge in self.BADGE_LIST:
            if badge['id'] not in self.badges_earned:
                # Simple condition check
                condition = badge['condition']
                if 'quizzes_played' in condition:
                    n = int(condition.split('>= ')[1])
                    if self.quizzes_played >= n:
                        self.badges_earned.append(badge['id'])
                elif 'total_score' in condition:
                    n = int(condition.split('>= ')[1])
                    if self.total_score >= n:
                        self.badges_earned.append(badge['id'])
                elif 'quizzes_created' in condition:
                    n = int(condition.split('>= ')[1])
                    if self.quizzes_created >= n:
                        self.badges_earned.append(badge['id'])
        self.save()

    def get_badges_display(self):
        result = []
        for badge in self.BADGE_LIST:
            result.append({
                **badge,
                'earned': badge['id'] in self.badges_earned
            })
        return result


# Signal to create profile on user creation
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
