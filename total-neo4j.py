from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
import os
from neo4j import GraphDatabase, exceptions

# 환경 변수 로드
load_dotenv()

# 환경 변수에서 설정 가져오기
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
llm_model_name = os.getenv("LLM_MODEL")
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_username = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")
neo4j_database = os.getenv("NEO4J_DATABASE")

# Neo4j 드라이버 객체 생성
class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query(self, query):
        with self.driver.session() as session:
            result = session.run(query)
            return [record for record in result]

# Neo4jConnection 객체 생성
graph = Neo4jConnection(neo4j_uri, neo4j_username, neo4j_password)

# Anthropic LLM 모델 객체 생성
llm_model = ChatAnthropic(
    model=llm_model_name,
    anthropic_api_key=anthropic_api_key,
    temperature=0.1,
    max_tokens=1024
)

# 템플릿 정의
template = PromptTemplate(
    template="""
    Task: Generate a valid Cypher query for Neo4j based on the user's question.

    Instructions:
    1. Provide only the Cypher query without any additional explanation or text.
    2. Ensure the query uses valid Cypher syntax.
    3. Use MATCH statements to define the relationships.
    4. Use RETURN to extract meaningful results.
    5. Assume that there are the following nodes with their respective properties:
       - 'Department' node with properties 'contact', 'email', 'location', and 'name'.
       - 'Admin' node with properties 'name', 'contact', 'email', 'location', 'description', and 'real_idx'.
       - 'Target' node with properties 'type', 'restriction', 'requirement', 'description', and 'real_idx'.
       - 'Portal' node with properties 'name', 'id', and 'url'.
       - 'Event' node with properties 'type', 'restriction', 'requirement', 'description', and 'real_idx'.
       - 'Schedule' node with properties 'title', 'start_date', 'end_date', and 'real_idx'.
       - 'ManageAt' node with properties 'type', 'method', 'location', 'description', and 'real_idx'.
    6. Relationships: 
       - (:Document)-[:HAS_EVENT]->(:Event)
       - (:Document)-[:MANAGE_AT]->(:Department)
       - (:Document)-[:MANAGE_AT]->(:Portal)
       - (:Document)-[:MANAGE_AT]->(:Admin)
       - (:Document)-[:SCHEDULE]->(:Target)

    Question: {question}

    Cypher Query:
    """,
    input_variables=["question"]
)

# 질문 루프
while True:
    question = input("질문을 입력해주세요 (종료하려면 '종료' 입력): ")
    if question.lower() == "종료":
        print("프로그램을 종료합니다.")
        break

    try:
        # LLM을 사용하여 Cypher 쿼리 생성
        prompt = template.format(question=question)  # 템플릿에 질문 포매팅
        response = llm_model.invoke(prompt)  # LLM 호출

        # AIMessage 객체에서 콘텐츠 추출
        generated_cypher = response.content.strip()

        # 불필요한 설명 제거
        if "Here is a Cypher query" in generated_cypher or \
           "이 쿼리는" in generated_cypher or \
           "이 질문은" in generated_cypher:
            # Extract only the Cypher query
            generated_cypher = generated_cypher.split("```")[-1].strip()

        # 유효한 Cypher 쿼리인지 확인
        if not generated_cypher or not ("MATCH" in generated_cypher and "RETURN" in generated_cypher):
            print("유효하지 않은 Cypher 쿼리 생성:", generated_cypher)
            continue

        print("생성된 Cypher 쿼리:", generated_cypher)

        result = graph.query(generated_cypher)
        if not result:
            print("Neo4j 실행 결과가 없습니다. 질문이나 데이터베이스를 확인해주세요.")
        else:
            print("Neo4j 실행 결과:")
            for record in result:
                print(record)
    except exceptions.CypherSyntaxError as e:
        print(f"Cypher 구문 오류 발생: {e}")
    except exceptions.ServiceUnavailable as e:
        print(f"Neo4j 서비스 불가 오류 발생: {e}")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        graph.close()
