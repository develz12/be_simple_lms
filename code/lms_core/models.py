import datetime
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

class Course(models.Model):
    name = models.CharField("Nama", max_length=255)
    description = models.TextField("Deskripsi")
    price = models.IntegerField("Harga")
    image = models.ImageField("Gambar", upload_to="course", blank=True, null=True)
    teacher = models.ForeignKey(User, verbose_name="Pengajar", on_delete=models.RESTRICT)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    max_students = models.IntegerField("Jumlah Maksimal Siswa", default=30)  
    created_at = models.DateTimeField("Dibuat pada", auto_now_add=True)
    updated_at = models.DateTimeField("Diperbarui pada", auto_now=True)

    def __str__(self):
        return self.name

    def is_full(self):
        return CourseMember.objects.filter(course_id=self).count() >= self.max_students

    def get_course_stats(self):
        return {
            'members_count': CourseMember.objects.filter(course_id=self).count(),
            'contents_count': CourseContent.objects.filter(course_id=self).count(),
            'comments_count': Comment.objects.filter(content_id__course_id=self).count(),
        }

    class Meta:
        verbose_name = "Mata Kuliah"
        verbose_name_plural = "Data Mata Kuliah"
        ordering = ["-created_at"]

    def is_member(self, user):
        return CourseMember.objects.filter(course_id=self, user_id=user).exists()
    
ROLE_OPTIONS = [('std', "Siswa"), ('ast', "Asisten")]

class CourseMember(models.Model):
    course_id = models.ForeignKey(Course, verbose_name="matkul", on_delete=models.RESTRICT)
    user_id = models.ForeignKey(User, verbose_name="siswa", on_delete=models.RESTRICT)
    roles = models.CharField("peran", max_length=3, choices=[('std', "Siswa"), ('ast', "Asisten")], default='std')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Subscriber Matkul"
        verbose_name_plural = "Subscriber Matkul"
        unique_together = ('course_id', 'user_id')

    def __str__(self):
        return f"{self.course_id.name} : {self.user_id.username}"

    def clean(self):
        if CourseMember.objects.filter(course_id=self.course_id, user_id=self.user_id).exists():
            raise ValidationError("Student is already enrolled in this course.")
        if self.course_id.is_full():
            raise ValidationError("Course has reached its maximum enrollment.")

class CourseContent(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nama Konten")
    description = models.TextField(verbose_name="Deskripsi")
    file_attachment = models.FileField("Lampiran File", null=True, blank=True)
    course_id = models.ForeignKey(
        "Course", verbose_name="Mata Kuliah", on_delete=models.RESTRICT
    )

    parent_id = models.ForeignKey(
        "self", verbose_name="Induk Konten", on_delete=models.RESTRICT, null=True, blank=True
    )
    scheduled_start_time = models.DateTimeField("Waktu Mulai", null=True, blank=True)
    scheduled_end_time = models.DateTimeField("Waktu Selesai", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diperbarui Pada")

    class Meta:
        verbose_name = "Konten Mata Kuliah"
        verbose_name_plural = "Konten Mata Kuliah"

    def __str__(self):
        return f"{self.course_id.name if self.course_id else 'No Course'} - {self.name}"

    def is_available(self):
        now = timezone.now()
        if self.scheduled_start_time and self.scheduled_end_time:
            return self.scheduled_start_time <= now <= self.scheduled_end_time
        if self.scheduled_start_time:
            return now >= self.scheduled_start_time
        if self.scheduled_end_time:
            return now <= self.scheduled_end_time
        return True

class Comment(models.Model):
    content_id = models.ForeignKey(CourseContent, verbose_name="konten", on_delete=models.CASCADE)
    member_id = models.ForeignKey(CourseMember, verbose_name="pengguna", on_delete=models.CASCADE)
    comment = models.TextField('komentar')
    is_approved = models.BooleanField('Disetujui', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Komentar"
        verbose_name_plural = "Komentar"

    def __str__(self):
        return f"Komen oleh {self.member_id.user_id.username}: {self.comment}"

class ContentCompletion(models.Model):
    content = models.ForeignKey(CourseContent, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('content', 'user')

    def __str__(self):
        return f'{self.user.username} completed {self.content.name}'

User.add_to_class('get_course_stats', lambda self: {
    'courses_as_student': CourseMember.objects.filter(user_id=self, roles='std').count(),
    'courses_created': Course.objects.filter(teacher=self).count(),
    'comments_written': Comment.objects.filter(member_id__user_id=self).count(),
    'contents_completed': ContentCompletion.objects.filter(user=self).count(),
})

class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    course = models.ForeignKey('Course', on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    def is_active(self):
        return self.start_date <= datetime.now() <= self.end_date

    class Meta:
        verbose_name = "Pengumuman"
        verbose_name_plural = "Pengumuman"

    def is_available(self):
        now = timezone.now()
        if self.start_date and self.end_date:
            return self.start_date <= now <= self.end_date
        if self.start_date:
            return now >= self.start_date
        if self.end_date:
            return now <= self.end_date
        return True

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="categories", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategori"