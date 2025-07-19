import asyncio
from acp_sdk.client import Client
from colorama import Fore

async def run_hospital_workflow() -> None:
    # Get the specific question part from user
    health_question = input("Enter your specific health question (e.g., 'Do I need rehabilitation after...'): ")
    
    async with Client(base_url="http://localhost:8001") as insurer, Client(base_url="http://localhost:8000") as hospital, Client(base_url="http://localhost:8002") as stock_info:
        run1 = await hospital.run_sync(
            agent="health_agent", 
            input=f"{health_question} Do not tell me to consult with medical professionals for personalized "
                  "advice. Give general advice that will not be taken as fact, and will be verified. "
                  "Always mention that this is general advice, and to consult a doctor at the end."
        )
        print(run1)
        content = run1.output[0].parts[0].content
        print(Fore.LIGHTMAGENTA_EX + content + Fore.RESET)

        run2 = await insurer.run_sync(
            agent="policy_agent", input=f"Context: {content} What is the waiting period for rehabilitation?"
        )
        print(Fore.YELLOW + run2.output[0].parts[0].content + Fore.RESET)

        run3 = await stock_info.run_sync(
            agent="mcp_agent",
            input=f"Context: {content} What is the stock info for insurance companies regarding this health query?"
                  f"If you can't generate an answer, default to AAPL stock ticker."
        )
        print(Fore.LIGHTCYAN_EX + run3.output[0].parts[0].content + Fore.RESET)


if __name__ == "__main__":
    asyncio.run(run_hospital_workflow())
