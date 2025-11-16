## LangChain
![3p-agentic-frameworks](assets/langchain-aws.png)

LangChain is the easiest way to start building agents and applications powered by LLMs. With under 10 lines of code, you can connect to models from Amazon Bedrock, Sagemaker, OpenAI, Anthropic, Google and more.

We recommend you use LangChain if you want to quickly build agents and autonomous applications. Use LangGraph, our low-level agent orchestration framework and runtime, when you have more advanced needs that require a combination of deterministic and agentic workflows, heavy customization, and carefully controlled latency.

## LangChain & LangGraph Official Documentation

**Docs:** https://docs.langchain.com/oss/python/langchain/overview

## LangChain + AWS

**Docs for LangChain and AWS Integrations:** https://docs.langchain.com/oss/python/integrations/providers/aws

LangChain supports a rich ecosystem AWS integrations for services such as :
* Amazon Bedrock
* Amazon Bedrock Knowledge Bases
* Amazon Sagemaker
* Amazon S3
* Amazon Textract
* Amazon Athena
* AWS Glue
* Amazon OpenSearch Service
* Amazon DocumentDB
* Amazon MemoryDB
* Amazon Kendra
* Amazon Lambda
* Amazon Neptune
* Amazon Comprehend

Please contact partnerships@langchain.dev for more integration support! 

### Importing LLMs from Amazon Bedrock

**Model IDs Supported in Amazon Bedrock:** https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html

**LLM Configuration:** 

Using Bedrock Endpoint (boto3):
```
from langchain_aws import ChatBedrockConverse 
from langchain_aws import ChatBedrock

bedrock_client = boto3.client("bedrock-runtime", region_name="<region_name>")

llm = ChatBedrockConverse(
        model="anthropic.claude-3-haiku-20240307-v1:0",
        temperature=0,
        max_tokens=None,
        client=bedrock_client,
        # other params...
    )

llm.invoke(input="What is the recipe of mayonnaise?")

```

Using Sagemaker Endpoint
```
from langchain_community.llms import SagemakerEndpoint

llm=SagemakerEndpoint(
        endpoint_name=endpoint_name,
        region_name="us-east-1",
        model_kwargs={"max_new_tokens": 500, "do_sample": True, "temperature": 0.001}, #extending the max_tokens is VITAL, as the response will otherwise be cut, breaking the agent functionality by not giving it access to the LLM's full answer. The value has been picked empirically
        content_handler=content_handler
    )
```