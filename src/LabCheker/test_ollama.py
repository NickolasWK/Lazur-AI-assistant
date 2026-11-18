import asyncio

from app.llm.ollama_client import evaluate_code


async def main():
    result = await evaluate_code(
        criteria_markdown="""
        1. Создать класс Student.
        2. Использовать List<Student>.
        """,
        source_code="""
        using System;
        using System.Collections.Generic;

        class Student
        {
            public string Name { get; set; }
        }

        class Program
        {
            static void Main()
            {
                List<Student> students = new List<Student>();
            }
        }
        """
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())