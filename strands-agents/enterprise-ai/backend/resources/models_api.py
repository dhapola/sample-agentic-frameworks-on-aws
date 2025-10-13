from flask_restful import Resource
from botocore.exceptions import ClientError, NoCredentialsError
from providers.bedrock_provider import get_bedrock_client
from utils.utility import Utility


class ModelsResource(Resource):
    def get(self):
        """
        Returns a list of available AI models from Amazon Bedrock
        """

        util = Utility()
        try:
            # Get the Bedrock client
            bedrock_client = get_bedrock_client()
            
            # Get foundation models
            models_response = bedrock_client.list_foundation_models()
            
            # Process the models and include inference profiles
            models = []
            for model in models_response.get('modelSummaries', []):
                # Filter models to only include those with ON_DEMAND inference type and ACTIVE status
                inference_types = model.get('inferenceTypesSupported', [])
                model_status = model.get('modelLifecycle', {}).get('status')
                model_id = model.get('modelId')
                
                if 'ON_DEMAND' in inference_types and model_status == 'ACTIVE':
                    model_info = {
                        "id": model_id,
                        "name": model.get('modelName'),
                        #
                    }
                    
                    models.append(model_info)
            

            # Get inference profiles
            profiles_response = bedrock_client.list_inference_profiles(
                typeEquals='SYSTEM_DEFINED',  
                maxResults=500             
            )
            
            # Create a dictionary of inference profiles for easy lookup

            for profile in profiles_response.get('inferenceProfileSummaries', []):
                # Only include ACTIVE inference profiles
                
                if profile.get('status') == 'ACTIVE':

                    model_info = {
                        "id": profile.get('inferenceProfileId'),
                        "name": profile.get('inferenceProfileName'),
                        # "provider": ''
                    }

                    models.append(model_info)

            return {
                "models": models,
                "count": len(models),
                "status": "success"
            }
            
        except NoCredentialsError:
            util.log_error("No AWS credentials found")
            return {
                "error": "AWS credentials not found",
                "details": "Please configure your AWS credentials",
                "status": "error"
            }, 500
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            error_message = e.response.get('Error', {}).get('Message')
            
            util.log_error(f"AWS Bedrock API error: {error_code} - {error_message}")
            
            return {
                "error": "Failed to retrieve models from Amazon Bedrock",
                "details": f"{error_code}: {error_message}",
                "status": "error"
            }, 500
            
        except Exception as e:
            util.log_error(f"Unexpected error: {str(e)}")
            
            return {
                "error": "An unexpected error occurred",
                "details": str(e),
                "status": "error"
            }, 500
