from .models import Quiz, Question, QuizComments, MultipleChoiceOption, QuizScoreBoard, User, QuizzesAttemptedByUser, AttemptedQuizByAnonymousUser, UserAnswerForQuestion
from rest_framework import serializers


from serializers import HostDetails, PartialUserSerializer, StudentAccountSerializer

from .helpers import evaluate_user_response

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
        user: User = data.get('user')
        anonymous_id = data.get('anonymous_id')
    
        if user:
            if user.is_authenticated:
                tracker = QuizzesAttemptedByUser.objects.filter(quiz=instance, student__user=user).first()
            else:
                tracker = AttemptedQuizByAnonymousUser.objects.filter(quiz=instance, anonymous_user__anonymous_id=anonymous_id).first()
                
            user_status = "continue-quiz" if (tracker and not tracker.is_completed) else ('is-completed' if tracker.is_completed else 'start-quiz')
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

    def to_representation(self, obj:Question):
        representation = super().to_representation(obj)
        representation['user_previous_response'] = None
        representation['multiple_answer_length'] = None
        
        data = self.context
        user:User = data.get('user')
        anonymous_id = data.get('anonymous_id')
        
        user_id = user.id if user.is_authenticated else anonymous_id
        user_answer = UserAnswerForQuestion.objects.filter(user_id=user_id, question=obj).first()

        if user_answer and obj.quiz.result_display_type == obj.quiz.ResultDisplayType.ON_COMPLETE:
            open_ended_response = user_answer.answer[0] if obj.question_type == obj.QuestionTypes.OPEN_ENDED else None
            result = evaluate_user_response(obj,user_answer.answer)
            representation['user_previous_response'] = {**result, 'open_ended_response': open_ended_response, 'show_answer': bool(user_answer and obj.quiz.result_display_type == obj.quiz.ResultDisplayType.ON_COMPLETE), 'user_answer': user_answer.answer}

        if obj.question_type == obj.QuestionTypes.MULTIPLE_CHOICES:
           multiple_answer_length = MultipleChoiceOption.objects.filter(question=obj, is_correct_answer=True).count()
           representation['multiple_answer_length'] = multiple_answer_length

        return representation

class QuizScoreBoardSerializer(serializers.ModelSerializer):
    user = StudentAccountSerializer(read_only=True)
    
    class Meta:
        fields = '__all__'
        model = QuizScoreBoard



