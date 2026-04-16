아키텍처 상의 host frontend, agent backend로 명명하여 개발을 진행하겠습니다. 
각 프로젝트는 독립적으로 개발되며, 테스트 주도 개발(TDD) 방식을 따릅니다. 아래는 각 프로젝트의 구조와 개발 계획입니다.

/agentic-ai-agent
|- host-frontend
|- agent-backend

1. host-frontend 개발(2이 성공하면 그때 소스코드를 작성해)
 - Java: 17.0.14 + Spring Boot, java lint 사용, 
 - java-springboot 스킬을 반드시 사용하여 해당 원칙에 맞게 개발 진행.
 - tester가 작성한 실패하는 테스트 기반으로 테스트를 통과하는 함수를 작성하며 개발 진행.
 - 테스트가 완전히 통과할때 까지 수정.
2. host-frontend-tester (TTD)
 - Java: 17.0.14 + Spring Boot + Junit
 - spring-boot-testing 스킬을 반드시 사용하여 원칙에 맞게 개발.
 - tester는 developer의 개발에 전혀 관여 하지않음.
5. agent-backend 개발 (5이 성공하면 그때 소스코드를 작성해)
 - Python: 3.11.11 + FastAPI, LangChain
6. agent-backend-tester (TDD)
 - Python: 3.11.11