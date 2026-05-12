from django.urls import path
from . import views
from . import admin_views

urlpatterns = [
    # ===== SITE PRINCIPAL =====
    path('', views.home, name='home'),
    path('quizzes/', views.quiz_list, name='quiz_list'),
    path('quiz/<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),
    path('quiz/<int:quiz_id>/play/', views.quiz_play, name='quiz_play'),
    path('quiz/<int:quiz_id>/save-score/', views.save_score, name='save_score'),
    path('quiz/create/', views.quiz_create, name='quiz_create'),
    path('quiz/<int:quiz_id>/edit/', views.quiz_edit, name='quiz_edit'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('profile/', views.profile, name='profile'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # ===== REJOINDRE PAR PIN =====
    path('join/', views.quiz_join, name='quiz_join'),
    path('join/<str:code>/', views.quiz_join_direct, name='quiz_join_direct'),

    # ===== PANNEAU ADMIN PERSONNALISÉ =====
    path('panel/', admin_views.admin_overview, name='admin_overview'),
    path('panel/users/', admin_views.admin_users, name='admin_users'),
    path('panel/users/create/', admin_views.admin_user_create, name='admin_user_create'),
    path('panel/users/<int:user_id>/edit/', admin_views.admin_user_edit, name='admin_user_edit'),
    path('panel/users/<int:user_id>/toggle/', admin_views.admin_user_toggle, name='admin_user_toggle'),
    path('panel/users/<int:user_id>/staff/', admin_views.admin_user_make_staff, name='admin_user_make_staff'),
    path('panel/users/<int:user_id>/delete/', admin_views.admin_user_delete, name='admin_user_delete'),
    path('panel/quizzes/', admin_views.admin_quizzes, name='admin_quizzes'),
    path('panel/quizzes/create/', admin_views.admin_quiz_create, name='admin_quiz_create'),
    path('panel/quizzes/<int:quiz_id>/edit/', admin_views.admin_quiz_edit, name='admin_quiz_edit'),
    path('panel/quizzes/<int:quiz_id>/toggle/', admin_views.admin_quiz_toggle, name='admin_quiz_toggle'),
    path('panel/quizzes/<int:quiz_id>/delete/', admin_views.admin_quiz_delete, name='admin_quiz_delete'),
    path('panel/stats/', admin_views.admin_stats, name='admin_stats'),
]
