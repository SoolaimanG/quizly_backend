from .models import Quiz, Question, QuizComments, MultipleChoiceOption, QuizScoreBoard, User, QuizzesAttemptedByUser, AttemptedQuizByAnonymousUser
from rest_framework import serializers


from serializers import HostDetails, PartialUserSerializer, StudentAccountSerializer

class QuizSerializer(serializers.ModelSerializer):
    category = serializers.CharField(read_only=True)
    host = HostDetails(read_only=True)
    participants_count = serializers.SerializerMethodField(read_only=True)
    total_questions = serializers.SerializerMethodField(read_only=True)
    comments_count = serializers.SerializerMethodField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Quiz
        exclude = ['participants']
        
        
    def get_participants_count(self, obj):
        return obj.participants.count()
    
    def get_comments_count(self, obj):
        return QuizComments.objects.filter(quiz=obj).count()
    
    def get_total_questions(self, obj):
        return Question.objects.filter(quiz_id=obj).count()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        data = self.context
        user = data.get('user')
        anonymous_id = data.get('anonymous_id')
    
        if user:
            if user.is_authenticated:
                tracker = QuizzesAttemptedByUser.objects.filter(quiz=instance, student__user=user).first()
            else:
                tracker = AttemptedQuizByAnonymousUser.objects.filter(quiz=instance, anonymous_user__anonymous_id=anonymous_id).first()

            user_status = "is-completed" if (tracker and tracker.is_completed) else ("continue-quiz" if tracker else "start-quiz")
            representation['user_status'] = user_status
        else:
            representation['user_status'] = 'start-quiz'
        
        return representation


class QuizCommentSerializer(serializers.ModelSerializer):
    user = PartialUserSerializer(read_only=True)
    
    class Meta:
        fields = '__all__'
        model = QuizComments

class MultipleChoiceOptionSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = MultipleChoiceOption
# 
class QuestionSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()
    class Meta:
        exclude = ['correct_answer_explanation', 'answer']
        model = Question
        
    def get_options(self, obj):
        question_options = MultipleChoiceOption.objects.filter(question=obj).all()
        data = MultipleChoiceOptionSerializer(question_options, many=True)
        return data.data

class QuizScoreBoardSerializer(serializers.ModelSerializer):
    user = StudentAccountSerializer(read_only=True)
    
    class Meta:
        fields = '__all__'
        model = QuizScoreBoard



