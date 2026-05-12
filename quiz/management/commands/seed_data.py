"""
Management command to seed sample quiz data
Usage: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from quiz.models import Quiz, Question, UserProfile


class Command(BaseCommand):
    help = 'Seed the database with sample quiz data'

    def handle(self, *args, **kwargs):
        # Create admin user
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@quickquiz.ma', 'admin123')
            self.stdout.write(self.style.SUCCESS('✅ Admin créé: admin / admin123'))
        else:
            admin = User.objects.get(username='admin')

        # Create demo users
        demo_users = []
        for i, (username, score) in enumerate([
            ('Ahmed_M', 4500), ('Fatima_K', 3800), ('Youssef_B', 3200),
            ('Nadia_R', 2800), ('Omar_L', 2100)
        ]):
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username, f'{username}@example.com', 'pass123')
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.total_score = score
                profile.quizzes_played = score // 200
                profile.best_score = min(score, 850)
                profile.save()
                demo_users.append(user)
                self.stdout.write(f'✅ Utilisateur créé: {username}')

        # Sample quizzes
        quizzes_data = [
            {
                'title': 'Capitales du monde',
                'description': 'Testez vos connaissances sur les capitales mondiales!',
                'category': 'Géographie',
                'difficulty': 'medium',
                'time_limit': 25,
                'questions': [
                    {
                        'text': 'Quelle est la capitale du Maroc ?',
                        'type': 'mcq',
                        'options': ['Casablanca', 'Rabat', 'Fès', 'Marrakech'],
                        'correct_answer': '1',
                        'explanation': 'Rabat est la capitale politique du Maroc depuis 1912.',
                        'points': 100,
                    },
                    {
                        'text': 'Quelle est la capitale de l\'Australie ?',
                        'type': 'mcq',
                        'options': ['Sydney', 'Melbourne', 'Canberra', 'Brisbane'],
                        'correct_answer': '2',
                        'explanation': 'Canberra est la capitale fédérale de l\'Australie, construite spécialement à cet effet.',
                        'points': 150,
                    },
                    {
                        'text': 'Paris est la capitale de la France.',
                        'type': 'truefalse',
                        'options': [],
                        'correct_answer': 'true',
                        'explanation': 'Paris est bien la capitale et la plus grande ville de France.',
                        'points': 50,
                    },
                    {
                        'text': 'Quelle est la capitale du Brésil ?',
                        'type': 'mcq',
                        'options': ['Rio de Janeiro', 'São Paulo', 'Brasília', 'Salvador'],
                        'correct_answer': '2',
                        'explanation': 'Brasília est la capitale du Brésil depuis 1960, remplaçant Rio de Janeiro.',
                        'points': 150,
                    },
                    {
                        'text': 'Quelle est la capitale du Japon ?',
                        'type': 'short',
                        'options': [],
                        'correct_answer': 'tokyo',
                        'accepted_answers': ['Tokyo', 'TOKYO'],
                        'explanation': 'Tokyo est la capitale et la plus grande ville du Japon.',
                        'points': 100,
                    },
                ]
            },
            {
                'title': 'Sciences générales',
                'description': 'Quiz de culture scientifique pour tous!',
                'category': 'Sciences',
                'difficulty': 'easy',
                'time_limit': 30,
                'questions': [
                    {
                        'text': 'Quelle est la formule chimique de l\'eau ?',
                        'type': 'mcq',
                        'options': ['H2O', 'CO2', 'NaCl', 'O2'],
                        'correct_answer': '0',
                        'explanation': 'H2O (2 atomes d\'hydrogène + 1 atome d\'oxygène)',
                        'points': 50,
                    },
                    {
                        'text': 'La Terre tourne autour du Soleil en 365 jours.',
                        'type': 'truefalse',
                        'options': [],
                        'correct_answer': 'true',
                        'explanation': 'La révolution terrestre dure exactement 365.25 jours, d\'où l\'année bissextile.',
                        'points': 50,
                    },
                    {
                        'text': 'Quel est le symbole chimique de l\'Or ?',
                        'type': 'mcq',
                        'options': ['Go', 'Ag', 'Au', 'Fe'],
                        'correct_answer': '2',
                        'explanation': 'Au vient du latin "Aurum". Ag est l\'argent, Fe est le fer.',
                        'points': 100,
                    },
                    {
                        'text': 'Combien d\'os y a-t-il dans le corps humain adulte ?',
                        'type': 'mcq',
                        'options': ['106', '206', '306', '406'],
                        'correct_answer': '1',
                        'explanation': 'Le corps humain adulte possède 206 os.',
                        'points': 100,
                    },
                ]
            },
            {
                'title': 'Histoire du monde',
                'description': 'Voyage dans l\'histoire mondiale!',
                'category': 'Histoire',
                'difficulty': 'hard',
                'time_limit': 35,
                'questions': [
                    {
                        'text': 'En quelle année a eu lieu la Révolution française ?',
                        'type': 'mcq',
                        'options': ['1776', '1789', '1799', '1815'],
                        'correct_answer': '1',
                        'explanation': 'La Révolution française a débuté en 1789 avec la prise de la Bastille.',
                        'points': 100,
                    },
                    {
                        'text': 'Quel empire a construit le Colisée à Rome ?',
                        'type': 'mcq',
                        'options': ['Empire grec', 'Empire romain', 'Empire ottoman', 'Empire byzantin'],
                        'correct_answer': '1',
                        'explanation': 'Le Colisée a été construit sous l\'Empire romain, inauguré en 80 après J.-C.',
                        'points': 100,
                    },
                    {
                        'text': 'La Seconde Guerre mondiale s\'est terminée en 1945.',
                        'type': 'truefalse',
                        'options': [],
                        'correct_answer': 'true',
                        'explanation': 'La WWII s\'est terminée le 2 septembre 1945 avec la capitulation du Japon.',
                        'points': 50,
                    },
                ]
            },
            {
                'title': 'Technologie & Informatique',
                'description': 'Maîtrisez-vous les nouvelles technologies ?',
                'category': 'Technologie',
                'difficulty': 'medium',
                'time_limit': 30,
                'questions': [
                    {
                        'text': 'Que signifie HTTP ?',
                        'type': 'mcq',
                        'options': [
                            'HyperText Transfer Protocol',
                            'High Tech Transfer Protocol',
                            'HyperText Transport Program',
                            'Home Transfer Text Protocol'
                        ],
                        'correct_answer': '0',
                        'explanation': 'HTTP (HyperText Transfer Protocol) est le protocole de communication du Web.',
                        'points': 100,
                    },
                    {
                        'text': 'Python est un langage de programmation orienté objet.',
                        'type': 'truefalse',
                        'options': [],
                        'correct_answer': 'true',
                        'explanation': 'Python supporte la POO mais aussi la programmation fonctionnelle et impérative.',
                        'points': 50,
                    },
                    {
                        'text': 'Quel est le moteur de recherche le plus utilisé au monde ?',
                        'type': 'mcq',
                        'options': ['Bing', 'Yahoo', 'Google', 'DuckDuckGo'],
                        'correct_answer': '2',
                        'explanation': 'Google détient plus de 90% des parts de marché des moteurs de recherche.',
                        'points': 50,
                    },
                    {
                        'text': 'Quel framework Python utilise le modèle MVT ?',
                        'type': 'short',
                        'options': [],
                        'correct_answer': 'django',
                        'accepted_answers': ['Django', 'DJANGO'],
                        'explanation': 'Django utilise le modèle MVT (Model-View-Template).',
                        'points': 150,
                    },
                ]
            },
        ]

        for qdata in quizzes_data:
            if not Quiz.objects.filter(title=qdata['title']).exists():
                quiz = Quiz.objects.create(
                    title=qdata['title'],
                    description=qdata['description'],
                    category=qdata['category'],
                    difficulty=qdata['difficulty'],
                    time_limit=qdata['time_limit'],
                    author=admin,
                    play_count=50 + (hash(qdata['title']) % 200),
                )
                for i, q in enumerate(qdata['questions']):
                    Question.objects.create(
                        quiz=quiz,
                        text=q['text'],
                        type=q['type'],
                        options=q.get('options', []),
                        correct_answer=q['correct_answer'],
                        accepted_answers=q.get('accepted_answers', []),
                        explanation=q.get('explanation', ''),
                        points=q.get('points', 100),
                        order=i,
                    )
                self.stdout.write(f'✅ Quiz créé: {qdata["title"]} ({len(qdata["questions"])} questions)')

        self.stdout.write(self.style.SUCCESS('\n🎉 Base de données initialisée avec succès!'))
        self.stdout.write(self.style.SUCCESS('   Admin: admin / admin123'))
        self.stdout.write(self.style.SUCCESS('   URL: http://localhost:8000'))
