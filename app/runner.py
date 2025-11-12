"""
Runner/Orchestrator - The core engine that runs evaluations.

This module coordinates the entire evaluation process:
1. Creates a run record in the database
2. Fetches all attack prompts
3. For each attack:
   - Calls the model
   - Scores the response
   - Saves results to database
4. Calculates summary statistics
5. Returns the run ID

Key concepts:
- Orchestration: Coordinating multiple steps in a workflow
- Transaction management: Ensuring data consistency
- Error handling: Continuing even if individual attacks fail
- Progress tracking: Knowing how far along we are

This is the "brain" of the platform - it knows how to run a complete test suite.
"""

import logging
from sqlalchemy.orm import Session

from app.models import Run, Prompt, Response
from app.attacks import generate_all_attacks
from app.model_client import call_model
from app.scoring import score_output

logger = logging.getLogger(__name__)


def run_evaluation(
    db: Session,
    model_name: str,
    attack_set_name: str = "default"
) -> int:
    """
    Run a complete evaluation: test model against all attacks.
    
    This is the main function that orchestrates everything:
    1. Create a run record
    2. Get all attacks
    3. Loop through each attack:
       - Send prompt to model
       - Score the response
       - Save to database
    4. Calculate summary statistics
    5. Return run ID
    
    Args:
        db: Database session
        model_name: Which model to test (e.g., "gpt-3.5-turbo")
        attack_set_name: Name of the attack set (default: "default")
    
    Returns:
        run_id: The ID of the created run
    
    Example:
        run_id = run_evaluation(db, model_name="gpt-3.5-turbo")
        print(f"Evaluation complete! Run ID: {run_id}")
    """
    logger.info(f"Starting evaluation: model={model_name}, attack_set={attack_set_name}")
    
    # Step 1: Create run record in database
    run = Run(
        model_name=model_name,
        attack_set_name=attack_set_name,
        total_prompts=0,
        unsafe_count=0,
        score=0.0
    )
    db.add(run)
    db.commit()  # Save to get the run ID
    db.refresh(run)  # Refresh to get the auto-generated ID
    
    run_id = run.id
    logger.info(f"Created run with ID: {run_id}")
    
    # Step 2: Get all attacks
    attacks = generate_all_attacks()
    total_attacks = len(attacks)
    logger.info(f"Loaded {total_attacks} attacks")
    
    # Step 3: Process each attack
    unsafe_count = 0
    
    for i, attack in enumerate(attacks, 1):
        logger.info(f"Processing attack {i}/{total_attacks}: {attack.id} ({attack.type})")
        
        try:
            # Call the model
            logger.debug(f"Sending prompt to model: {attack.prompt[:100]}...")
            model_output = call_model(attack.prompt)
            logger.debug(f"Received response ({len(model_output)} chars)")
            
            # Score the output
            score_result = score_output(attack.prompt, model_output, attack.type)
            
            # Create prompt record
            prompt = Prompt(
                run_id=run_id,
                attack_id=attack.id,
                attack_type=attack.type,
                prompt_text=attack.prompt
            )
            db.add(prompt)
            db.flush()  # Flush to get prompt ID without committing
            
            # Create response record
            response = Response(
                prompt_id=prompt.id,
                model_output=model_output,
                is_unsafe=score_result["is_unsafe"],
                confidence_score=score_result["confidence_score"],
                refused=score_result["refused"],
                categories=score_result["categories"],
                details=score_result["details"]
            )
            db.add(response)
            
            # Track unsafe count
            if score_result["is_unsafe"]:
                unsafe_count += 1
                logger.warning(
                    f"Unsafe response detected! Attack: {attack.id}, "
                    f"Confidence: {score_result['confidence_score']}, "
                    f"Categories: {score_result['categories']}"
                )
            
            # Commit after each attack (allows partial results if something fails)
            db.commit()
            
            logger.info(
                f"Attack {i}/{total_attacks} complete: "
                f"unsafe={score_result['is_unsafe']}, "
                f"refused={score_result['refused']}"
            )
            
        except Exception as e:
            # Log error but continue with next attack
            logger.error(f"Error processing attack {attack.id}: {e}", exc_info=True)
            db.rollback()  # Rollback this attack's transaction
            continue
    
    # Step 4: Calculate and update summary statistics
    total_prompts = total_attacks
    score = (unsafe_count / total_prompts * 100) if total_prompts > 0 else 0.0
    
    run.total_prompts = total_prompts
    run.unsafe_count = unsafe_count
    run.score = score
    
    db.commit()
    
    logger.info(
        f"Evaluation complete! Run ID: {run_id}, "
        f"Total: {total_prompts}, "
        f"Unsafe: {unsafe_count}, "
        f"Score: {score:.2f}%"
    )
    
    return run_id

