from django.contrib import admin
from .models import Quiz, Question, QuizResult, UserProfile


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'difficulty', 'author', 'play_count', 'is_published', 'created_at']
    list_filter = ['category', 'difficulty', 'is_published']
    search_fields = ['title', 'description']
    list_editable = ['is_published']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'type', 'text', 'correct_answer', 'points', 'order']
    list_filter = ['type', 'quiz']


@admin.register(QuizResult)
class QuizResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'quiz', 'score', 'correct', 'wrong', 'played_at']
    list_filter = ['quiz']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_score', 'quizzes_played', 'quizzes_created', 'best_score']
    ordering = ['-total_score']
