from rest_framework import serializers
import os

class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    image_name = serializers.CharField()
    image_tag = serializers.CharField()

    def validate(self, data):
        
        if not data["file"]:
            raise serializers.ValidationError("File cannot be empty.")

        if not data["image_name"]:
            raise serializers.ValidationError("Image name cannot be empty.")
        
        if not data['image_tag']:
            raise serializers.ValidationError("Image tag cannot be empty.")

        name, ext = os.path.splitext(data["file"].name)
        if ext:
            raise serializers.ValidationError("File must not have any extension.")
        
        return data