from openai import OpenAI
client = OpenAI()

result = client.responses.create(
    model="gpt-5",
    input="Write a haiku about code.",
    reasoning={ "effort": "low" },
    text={ "verbosity": "low" },
)

print(result.output_text)

from openai import OpenAI
import json, os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

schema = {
    "name": "article_summary",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "keywords": {"type": "array", "items": {"type": "string"}},
            "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
            "score": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["title", "keywords", "sentiment", "score"],
    },
    "strict": True,
}

res = client.responses.create(
    model="gpt-5",
    input="次の文章を要約して: ...",
    text={"format": {"type": "json_schema", "json_schema": schema}},
    max_output_tokens=800,
)

data = json.loads(res.output_text)
print(data["title"], data["score"])