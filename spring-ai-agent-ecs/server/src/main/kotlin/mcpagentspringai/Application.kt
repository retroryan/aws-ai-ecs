package mcpagentspringai

import org.springframework.ai.tool.annotation.Tool
import org.springframework.ai.tool.annotation.ToolParam
import org.springframework.ai.tool.method.MethodToolCallbackProvider
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication
import org.springframework.context.annotation.Bean
import org.springframework.stereotype.Service

@SpringBootApplication
class Application {
    @Bean
    fun mcpTools(myTools: MyTools): MethodToolCallbackProvider =
        MethodToolCallbackProvider.builder().toolObjects(myTools).build()
}

data class AgricultureExpert(val id: String, val name: String, val skills: List<String>)

@Service
class MyTools {

    @Tool(description = "agriculture experts have skills. this returns all possible skills our agriculture experts have")
    fun getSkills(): Set<String> =
        SampleData.agricultureExperts.flatMap { it.skills }.toSet()

    @Tool(description = "get the agriculture experts that have a specific skill")
    fun getAgricultureExpertsWithSkill(@ToolParam(description = "skill") skill: String): List<AgricultureExpert> =
        SampleData.agricultureExperts.filter { expert ->
            expert.skills.any { it.equals(skill, ignoreCase = true) }
        }

    @Tool(description = "get a personalized agricultural recommendation from a specific agriculture expert by their ID. Use this after finding experts with getAgricultureExpertsWithSkill to get expert advice.")
    fun getRecommendationFromExpert(@ToolParam(description = "the unique ID of the agriculture expert (e.g., expert-001)") expertId: String): Map<String, Any?> {
        val expert = SampleData.agricultureExperts.find { it.id == expertId }
        return if (expert != null) {
            // Get recommendations based on expert's skills
            val skillBasedRecommendations = expert.skills.mapNotNull { skill ->
                SampleData.skillBasedRecommendations[skill]?.random()
            }
            
            val recommendation = if (skillBasedRecommendations.isNotEmpty()) {
                skillBasedRecommendations.random()
            } else {
                "Focus on continuous learning and staying updated with the latest agricultural technologies and practices."
            }
            
            mapOf(
                "expertId" to expertId,
                "expertName" to expert.name,
                "expertSkills" to expert.skills,
                "recommendation" to recommendation,
                "recommendationContext" to "This recommendation is tailored to the expert's specialization in: ${expert.skills.joinToString(", ")}"
            )
        } else {
            mapOf(
                "error" to "Expert not found with ID: $expertId",
                "availableExperts" to SampleData.agricultureExperts.take(5).map { "${it.id} (${it.name})" }
            )
        }
    }
    
    @Tool(description = "get a personalized agricultural recommendation from an expert with a specific specialty/skill. Provide a skill like 'Pest Management' or 'Crop Science' to get expert advice.")
    fun getRecommendationBySpecialty(@ToolParam(description = "the specialty or skill to get a recommendation for (e.g., 'Pest Management', 'Crop Science')") specialty: String): Map<String, Any?> {
        // Find experts with this specialty
        val expertsWithSpecialty = SampleData.agricultureExperts.filter { expert ->
            expert.skills.any { it.equals(specialty, ignoreCase = true) }
        }
        
        return if (expertsWithSpecialty.isNotEmpty()) {
            // Pick a random expert from those with this specialty
            val expert = expertsWithSpecialty.random()
            
            // Get recommendations specific to the requested specialty
            val recommendations = SampleData.skillBasedRecommendations[specialty]
                ?: SampleData.skillBasedRecommendations.entries
                    .firstOrNull { it.key.equals(specialty, ignoreCase = true) }
                    ?.value
            
            val recommendation = recommendations?.random() 
                ?: "Focus on continuous learning and staying updated with the latest agricultural technologies and practices in $specialty."
            
            mapOf(
                "specialty" to specialty,
                "expertId" to expert.id,
                "expertName" to expert.name,
                "expertSkills" to expert.skills,
                "recommendation" to recommendation,
                "recommendationContext" to "This recommendation is from ${expert.name}, an expert specializing in $specialty"
            )
        } else {
            mapOf(
                "error" to "No experts found with specialty: $specialty",
                "availableSpecialties" to SampleData.skills,
                "suggestion" to "Try one of the available specialties listed above"
            )
        }
    }
}

fun main(args: Array<String>) {
    SampleData.agricultureExperts.forEach { println(it) }
    runApplication<Application>(*args)
}
