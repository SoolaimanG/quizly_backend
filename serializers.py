from rest_framework import serializers
from base.models import ForgetPassword,Category, Quiz, Question, ObjectiveOptions ,TeachersAccount, StudentAccount, Comments, AttemptedQuizOfUser, Notifications, User
from django.db.models import Q
from base.helpers import string_mistakes
from django.utils import timezone
# from communites import serializers

class UserSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    first_time_login = serializers.BooleanField()
    last_login = serializers.DateTimeField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    id = serializers.UUIDField()
    is_active = serializers.BooleanField()
    email_verified = serializers.BooleanField()
    signup_complete = serializers.BooleanField()
    auth_provider = serializers.CharField()
    account_type = serializers.CharField()
    profile_image = serializers.ImageField()
    date_joined = serializers.DateTimeField()
    bio = serializers.CharField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data
  
class ForgetPasswordSerializer(serializers.ModelSerializer):
 
 class Meta:
   model = ForgetPassword
   fields = ['expires_by']
   
class CategorySerializer(serializers.ModelSerializer):
  class Meta:
    model = Category
    fields = ['body']
 
class TeachersAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachersAccount
        fields = '__all__'

class StudentAccountSerializer(serializers.ModelSerializer):
  class Meta:
    model = StudentAccount
    fields = '__all__'

class HostDetails(serializers.ModelSerializer):
    profile_image = serializers.ImageField(source='user.profile_image', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    bio = serializers.CharField(source='user.bio')

    class Meta:
        model = TeachersAccount
        fields = ['profile_image', 'username', 'user_id', 'bio','phone_num']

class QuizSerializer(serializers.ModelSerializer):
    category = serializers.CharField(read_only=True)
    host = HostDetails(read_only=True)
    participants_count = serializers.SerializerMethodField(read_only=True)
    total_questions = serializers.SerializerMethodField(read_only=True)
    comments_count = serializers.SerializerMethodField(read_only=True)
    has_user_started_quiz = serializers.BooleanField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Quiz
        exclude = ['participants']
        
    def get_participants_count(self, obj):
        return obj.participants.count()
    
    def get_comments_count(self, obj):
        return Comments.objects.filter(quiz=obj).count()
    
    def get_total_questions(self, obj):
        return Question.objects.filter(quiz_id=obj).count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        

        data['has_user_started_quiz'] = self.context.get('has_user_started_quiz', False)
        data['is_completed'] = self.context.get('is_completed', False)
        
        return data

class UUIDListSerializer(serializers.Serializer):
    uuids = serializers.ListField(child=serializers.UUIDField())
  
class QuestionSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField(read_only=True)
    correct_answer_length = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Question
        exclude = ['correct_answer_explanation','answer']
  
    def get_options(self, obj):
        options_queryset = ObjectiveOptions.objects.filter(belongs_to=obj)
        options_serializer = ObjectiveOptionsSerializer(options_queryset, many=True)
        return options_serializer.data
    
    def get_correct_answer_length(self, obj:Question):
      return  ObjectiveOptions.objects.filter(
        Q(belongs_to=obj) & Q(is_correct_answer=True)
      ).count()
    
class ObjectiveOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectiveOptions
        exclude = ['belongs_to']
        
class ObjectiveOptionSerializer(serializers.ModelSerializer):
  class Meta:
    model = ObjectiveOptions
    fields ='__all__'
  
  def to_representation(self, instance):
    return super().to_representation(instance) 

class CommentsSerializer(serializers.ModelSerializer):
  username = serializers.CharField(source='user.username')
  profile_image = serializers.ImageField(source='user.profile_image')
  
  class Meta:
    model = Comments
    fields = ['username','profile_image','body','created_at','id']

class SubmitQuizSerializer(serializers.Serializer):
  total_questions = serializers.SerializerMethodField()
  wrong_answers = serializers.SerializerMethodField()
  time_taken = serializers.SerializerMethodField()
  
  class Meta:
    model = AttemptedQuizOfUser
    fields = ['xp', 'questions_answered_by_student', 'total_questions', 'wrong_answers', 'time_taken']
    
  
  def get_total_questions(self, instance:AttemptedQuizOfUser):
    questions = Question.objects.filter(quiz_id=instance.quiz).count()
    
    return questions
  
  def get_wrong_answers(self, instance: AttemptedQuizOfUser):
    wrong_answer = []
    get_all_questions = Question.objects.filter(quiz_id=instance.quiz).all()

    for question in get_all_questions:
        question_type = question.question_type
        user_answer_entry = next(
            (entry for entry in instance.answers if entry['question_id'] == str(question.id)),
            None
        )

        if user_answer_entry is not None:
            user_answer = user_answer_entry['user_answer']

            if question_type == Question.QuestionTypes.OBJECTIVE:
                objective_question = question.objectiveoptions_set.filter(is_correct_answer=True).first()

                # Compare the user's answer with the correct answer
                if user_answer != str(objective_question.id):
                    wrong_answer.append({
                        'question': str(question.id),
                        'correct_answer': question.question_body,
                    })
            
            if question_type == Question.QuestionTypes.MULTIPLE_CHOICES:
              correct_options:ObjectiveOptions = question.objectiveoptions_set.filter(is_correct_answer=True)
              
              if not all(i.body in user_answer for i in correct_options ):
                wrong_answer.append({
                  'question': str(question.question_body),
                  'correct_answer': " ,".join([i.body for i in correct_options]),
                })
                
            if question_type == Question.QuestionTypes.GERMAN:
              
              if question.is_strict:
                if user_answer.lower().strip() != question.answer.lower().strip():
                  wrong_answer.append({
                    'question': str(question.question_body),
                    'correct_answer': str(question.answer)
                  })
              else:
                mistakes_in_question = string_mistakes(user_answer, question.answer)
                if mistakes_in_question > question.mistakes_to_ignore:
                  wrong_answer({
                    'question': question.question_body,
                    'correct_answer':question.answer
                  })

    return wrong_answer
  
  def get_time_taken(self, instance:AttemptedQuizOfUser):
    start_time = instance.start_time
    current_time = timezone.now()
    
    time_taken = current_time - start_time
    return time_taken

class AttemptedQuestionSerializer(serializers.Serializer):
  question = serializers.CharField()
  correct_answer = serializers.CharField()

class ResultSerializer(serializers.Serializer):
    feedback = serializers.CharField()
    xp_earn = serializers.IntegerField()
    attempted_questions = serializers.IntegerField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    wrong_answers = serializers.IntegerField()
    corrections = AttemptedQuestionSerializer(many=True)
    total_questions = serializers.IntegerField()
    expected_xp = serializers.IntegerField()

    def to_representation(self, instance):
        return super().to_representation(instance)
  
  #def to_representation(self, instance):
  #   return super().to_representation(instance)

class ImageSerializer(serializers.Serializer):
   image = serializers.ImageField()

class RelatedQuizSerializer(serializers.Serializer):

   quiz__id = serializers.UUIDField(read_only=True)
   quiz__title = serializers.CharField()

class RelatedQuizSerializerForTutor(serializers.Serializer):
   id = serializers.UUIDField(read_only=True)
   title = serializers.CharField()

class PartialUserSerializer(serializers.ModelSerializer):
   username = serializers.CharField()
   profile_image = serializers.URLField( required=False)
   id = serializers.UUIDField()

   class Meta:
      model = User
      fields = ['profile_image', 'username', 'id', 'account_type']
 
class PartialQuizSerializer(serializers.ModelSerializer):
   title = serializers.CharField()
   banner = serializers.URLField(required=False)
   id = serializers.UUIDField()
   host = HostDetails(read_only=True)

   class Meta:
      model = Quiz
      fields = ['title', 'banner', 'id', 'host']
 
class NotificationSerializer(serializers.ModelSerializer):
   
   user = PartialUserSerializer(read_only=True)
   user_requesting = PartialUserSerializer(read_only=True)
   quiz = PartialQuizSerializer(read_only=True)
   
   class Meta:
      fields = '__all__'
      model = Notifications
  
  
  