from django.contrib import admin
from django.template.defaultfilters import filesizeformat
from .models import PatientArchive, ArchiveAttachment


class ArchiveAttachmentInline(admin.TabularInline):
    model = ArchiveAttachment
    extra = 1
    readonly_fields = ['uploaded_at']
    fields = ['file', 'description', 'uploaded_at']
    show_change_link = True
    verbose_name = "Attachment"
    verbose_name_plural = "Archive Attachments"


@admin.register(PatientArchive)
class PatientArchiveAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'doctor', 'title',
        'archive_type', 'is_critical_display', 'created_at'
    ]
    list_filter = ['archive_type', 'is_critical', 'created_at']
    search_fields = ['title', 'notes', 'patient__full_name', 'doctor__user__full_name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ArchiveAttachmentInline]

    @admin.display(description="Critical", boolean=True)
    def is_critical_display(self, obj):
        return obj.is_critical


@admin.register(ArchiveAttachment)
class ArchiveAttachmentAdmin(admin.ModelAdmin):
    list_display = [
        'short_file_name', 'archive', 'uploaded_at', 'file_size_display'
    ]
    search_fields = ['file', 'description']
    readonly_fields = ['uploaded_at']

    @admin.display(description="File Name")
    def short_file_name(self, obj):
        return obj.file.name.split('/')[-1]

    @admin.display(description="Size")
    def file_size_display(self, obj):
        return filesizeformat(obj.file.size)
