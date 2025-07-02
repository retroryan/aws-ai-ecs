package mcpagentspringai

import io.modelcontextprotocol.client.McpSyncClient
import org.slf4j.LoggerFactory
import org.springframework.ai.chat.client.ChatClient
import org.springframework.ai.mcp.SyncMcpToolCallbackProvider
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication
import org.springframework.context.annotation.Bean
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RestController
import jakarta.annotation.PostConstruct
import org.springframework.beans.factory.annotation.Value


@SpringBootApplication
class Application {
    private val logger = LoggerFactory.getLogger(Application::class.java)
    
    @Value("\${SPRING_AGRICULTURE_EXPERTS_URL:http://localhost:8010}")
    private lateinit var mcpServiceUrl: String
    
    @Value("\${spring.ai.bedrock.aws.region:us-east-1}")
    private lateinit var awsRegion: String
    
    @Value("\${spring.ai.bedrock.nova.chat.model:nova-pro-v1:0}")
    private lateinit var bedrockModel: String
    
    @PostConstruct
    fun logStartup() {
        logger.info("=== MCP Client/Agent Application Starting ===")
        logger.info("MCP Service URL: $mcpServiceUrl")
        logger.info("AWS Region: $awsRegion")
        logger.info("Bedrock Model: $bedrockModel")
    }
    
    @Bean
    fun chatClient(mcpSyncClients: List<McpSyncClient>, builder: ChatClient.Builder): ChatClient {
        logger.info("Configuring ChatClient with ${mcpSyncClients.size} MCP client(s)")
        return builder
            .defaultToolCallbacks(SyncMcpToolCallbackProvider(mcpSyncClients))
            .build()
    }
}

data class Prompt(val question: String)

@RestController
class ConversationalController(val chatClient: ChatClient) {
    
    private val logger = LoggerFactory.getLogger(ConversationalController::class.java)

    @PostMapping("/inquire")
    fun inquire(@RequestBody prompt: Prompt): String {
        logger.info("Received inquiry: ${prompt.question}")
        
        val systemMessage = """
            You are an agricultural expert assistant with access to a database of agriculture experts and their specializations.
            
            When providing information about agriculture experts:
            - Always include the expert's ID (e.g., expert-001) when mentioning specific experts
            - Format expert information clearly showing: ID, Name, and Skills
            - When getting recommendations, always mention which expert provided the advice
            - Be helpful and provide detailed agricultural guidance
            
            Available tools:
            - getSkills(): Get all available agriculture skills
            - getAgricultureExpertsWithSkill(skill): Find experts with specific skills (returns ID, name, and skills)
            - getRecommendationFromExpert(expertId): Get personalized recommendations from specific experts by their ID
            - getRecommendationBySpecialty(specialty): Get recommendations directly by specialty (e.g., 'Pest Management', 'Crop Science')
            
            You can use getRecommendationBySpecialty when users ask for recommendations about a specific area without needing to find experts first.
        """.trimIndent()
        
        val response = chatClient
                .prompt()
                .system(systemMessage)
                .user(prompt.question)
                .call()
                .content() ?: "Please try again later."
                
        logger.info("Generated response length: ${response.length} characters")
        return response
    }
}


fun main(args: Array<String>) {
    runApplication<Application>(*args)
}
