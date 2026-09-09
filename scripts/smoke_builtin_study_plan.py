"""对内置检索与真实结构化生成做不写业务数据的冒烟检查。"""

import argparse

from app.api.dependencies import build_embedder, build_llm_client, build_vector_index
from app.core.config import get_settings, parse_builtin_document_ids
from app.llm.prompts import build_study_plan_prompt
from app.schemas.study_plan import GeneratedStudyPlan
from app.services.search import KnowledgeSearchService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", help="需要检查的技能原文")
    args = parser.parse_args()
    skill = args.skill.strip()
    if not skill:
        raise ValueError("skill cannot be blank")

    settings = get_settings()
    document_ids = parse_builtin_document_ids(settings.rag_builtin_document_ids)
    if not document_ids:
        raise RuntimeError("RAG_BUILTIN_DOCUMENT_IDS is not configured")

    search = KnowledgeSearchService(
        embedder=build_embedder(settings.rag_embedding_model),
        vector_index=build_vector_index(
            settings.rag_chroma_path,
            settings.rag_builtin_collection_name,
        ),
        default_max_distance=settings.rag_max_distance,
    )
    results = search.search(
        query=skill,
        top_k=settings.rag_plan_top_k,
        document_ids=document_ids,
    ).results
    if not results:
        raise RuntimeError("No eligible built-in evidence was retrieved")

    client = build_llm_client(settings)
    try:
        generated = client.complete_structured(
            prompt=build_study_plan_prompt(
                [skill],
                {skill: [(result.chunk_id, result.text) for result in results]},
            ),
            response_model=GeneratedStudyPlan,
        )
    finally:
        close = getattr(client, "close", None)
        if close is not None:
            close()

    if [item.skill for item in generated.skills] != [skill]:
        raise RuntimeError("Provider output changed the target skill")
    allowed_ids = {result.chunk_id for result in results}
    cited_ids = {
        evidence_id
        for item in generated.skills
        for task in item.tasks
        for evidence_id in task.evidence_ids
    }
    if not cited_ids <= allowed_ids:
        raise RuntimeError("Provider output cited evidence outside retrieval results")

    item = generated.skills[0]
    print(
        f"skill={skill} retrieved={len(results)} support={item.support_status} "
        f"tasks={len(item.tasks)} citations={len(cited_ids)}"
    )
    for index, task in enumerate(item.tasks, start=1):
        print(f"task[{index}] phase={task.phase.value} title={task.title}")


if __name__ == "__main__":
    main()
