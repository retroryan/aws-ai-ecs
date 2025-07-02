package mcpagentspringai

import kotlin.random.Random

object SampleData {

    private val firstNames = listOf("Ethan", "Emma", "Mason", "Olivia", "Jackson", "Sophia", "Lucas", "Ava", "Noah", "Isabella")
    private val lastNames = listOf("Fields", "Harvest", "Meadows", "Rivers", "Stone", "Woods", "Prairie", "Storm", "Green", "Weather")

    val skills = listOf(
        "Crop Science", "Soil Analysis", "Irrigation Systems", "Pest Management", "Livestock Care", "Weather Forecasting",
        "Climate Modeling", "Precision Agriculture", "Hydroponics", "Organic Farming", "Cattle Ranching", "Meteorology",
        "Sustainable Farming", "Agricultural Economics", "Farm Equipment", "GPS Technology", "Drone Operations", "Data Analytics",
        "Crop Rotation", "Animal Husbandry", "Weather Monitoring", "Drought Management", "Fertilizer Application", "Harvest Planning"
    )

    val agricultureExperts = List(100) { index ->
        AgricultureExpert(
            id = "expert-${String.format("%03d", index + 1)}",
            name = firstNames.random() + " " + lastNames.random(),
            skills = List(Random.nextInt(2, 6)) { skills.random() }.distinct()
        )
    }.distinctBy { it.name }

    val skillBasedRecommendations = mapOf(
        "Crop Science" to listOf(
            "Implement crop rotation with nitrogen-fixing legumes to naturally enhance soil fertility and reduce synthetic fertilizer dependency.",
            "Consider hybrid varieties that are resistant to local pests and diseases while maintaining high yield potential.",
            "Use precision seeding technology to optimize plant spacing and improve overall yield potential.",
            "Monitor crop phenology stages closely to optimize timing for fertilizer application and pest management."
        ),
        "Soil Analysis" to listOf(
            "Conduct regular soil tests every 2-3 years to monitor pH, nutrient levels, and organic matter content.",
            "Implement variable rate fertilization based on soil test results to optimize nutrient application.",
            "Monitor and manage soil pH levels to optimize nutrient availability and crop performance.",
            "Use soil moisture sensors to track water retention and drainage patterns across different field zones."
        ),
        "Irrigation Systems" to listOf(
            "Install soil moisture sensors to optimize irrigation scheduling and reduce water usage by 20-30%.",
            "Invest in water-efficient irrigation systems like drip irrigation to conserve water resources.",
            "Implement smart irrigation controllers that adjust watering based on weather forecasts and soil conditions.",
            "Consider deficit irrigation strategies during non-critical growth stages to improve water use efficiency."
        ),
        "Pest Management" to listOf(
            "Adopt integrated pest management (IPM) strategies to reduce pesticide use while maintaining effective control.",
            "Use beneficial insects and natural predators to control pest populations instead of relying solely on chemicals.",
            "Implement crop rotation and companion planting to naturally disrupt pest life cycles.",
            "Monitor pest thresholds regularly and apply treatments only when economically justified."
        ),
        "Livestock Care" to listOf(
            "Use precision livestock farming techniques to monitor animal health and optimize feed efficiency.",
            "Implement rotational grazing systems to improve pasture health and animal nutrition.",
            "Invest in automated feeding systems to ensure consistent nutrition and reduce labor costs.",
            "Monitor animal behavior and health indicators using wearable technology for early disease detection."
        ),
        "Weather Forecasting" to listOf(
            "Monitor weather patterns closely and adjust planting schedules to optimize growing conditions.",
            "Use weather data to optimize spray timing and reduce application losses due to wind or rain.",
            "Implement frost protection measures based on accurate weather forecasting systems.",
            "Adjust harvest timing based on extended weather forecasts to minimize crop losses."
        ),
        "Climate Modeling" to listOf(
            "Implement climate-smart agriculture practices to adapt to changing weather patterns and reduce risks.",
            "Use historical climate data to select crop varieties best suited for your changing local conditions.",
            "Plan long-term crop rotations based on projected climate trends and precipitation patterns.",
            "Consider drought-resistant varieties and water conservation practices for future climate resilience."
        ),
        "Precision Agriculture" to listOf(
            "Implement precision agriculture techniques to optimize fertilizer application and reduce costs by up to 15%.",
            "Use GPS-guided equipment to reduce overlap and improve field efficiency by 5-10%.",
            "Implement variable rate technology (VRT) for precise application of seeds, fertilizers, and pesticides.",
            "Use drone technology and satellite imagery for crop monitoring and variable rate applications."
        ),
        "Hydroponics" to listOf(
            "Consider aquaponics or hydroponics systems for high-value crop production in controlled environments.",
            "Optimize nutrient solutions based on plant growth stages and environmental conditions.",
            "Implement automated pH and EC monitoring systems for consistent hydroponic production.",
            "Use vertical growing systems to maximize production per square foot in hydroponic facilities."
        ),
        "Organic Farming" to listOf(
            "Consider transitioning to organic farming methods to access premium markets and reduce input costs long-term.",
            "Use cover crops during off-seasons to prevent soil erosion and improve organic matter content.",
            "Implement biological control agents to manage soil-borne diseases naturally and sustainably.",
            "Focus on soil health improvement through composting and natural amendments."
        ),
        "Cattle Ranching" to listOf(
            "Practice strategic grazing management to improve pasture health and livestock performance.",
            "Implement rotational grazing to prevent overgrazing and improve soil health.",
            "Monitor cattle weight gain and adjust feeding programs based on seasonal pasture quality.",
            "Use genetic selection to improve herd disease resistance and production efficiency."
        ),
        "Meteorology" to listOf(
            "Use weather monitoring stations to collect micro-climate data for precise farming decisions.",
            "Implement frost prediction systems to protect sensitive crops during critical periods.",
            "Monitor growing degree days to optimize planting and harvest timing.",
            "Use weather data integration with farm management software for automated decision support."
        ),
        "Sustainable Farming" to listOf(
            "Implement regenerative agriculture practices to restore ecosystem health while maintaining productivity.",
            "Use carbon farming practices to potentially access carbon credit markets while improving soil health.",
            "Consider permaculture design principles to create sustainable and self-maintaining agricultural systems.",
            "Implement buffer strips around water bodies to prevent nutrient runoff and protect water quality."
        ),
        "Agricultural Economics" to listOf(
            "Monitor commodity prices and use forward contracts to reduce market risk and secure better prices.",
            "Consider value-added processing opportunities to capture more profit from your agricultural products.",
            "Implement digital record-keeping systems to track inputs, yields, and profitability more accurately.",
            "Diversify income streams through specialty crops or agritourism to reduce market dependency."
        ),
        "Farm Equipment" to listOf(
            "Upgrade to GPS-guided equipment to reduce overlap and improve field efficiency by 5-10%.",
            "Consider collaborative farming approaches to share equipment costs and access larger markets.",
            "Implement preventive maintenance schedules to reduce equipment downtime during critical periods.",
            "Invest in multi-functional equipment to reduce overall machinery costs and improve efficiency."
        ),
        "GPS Technology" to listOf(
            "Use GPS guidance systems to create precise field maps and reduce input overlap.",
            "Implement GPS-based soil sampling for accurate nutrient management mapping.",
            "Use RTK GPS for sub-inch accuracy in precision agriculture applications.",
            "Integrate GPS data with farm management software for comprehensive field tracking."
        ),
        "Drone Operations" to listOf(
            "Use drone technology for crop monitoring to identify issues early and take corrective action promptly.",
            "Implement drone-based variable rate application for targeted pest and disease management.",
            "Use thermal imaging drones to detect irrigation issues and plant stress patterns.",
            "Conduct regular drone surveys to monitor crop growth and identify problem areas quickly."
        ),
        "Data Analytics" to listOf(
            "Use predictive analytics and AI tools to optimize decision-making and improve farm management efficiency.",
            "Implement data-driven crop modeling to optimize planting dates and variety selection.",
            "Use machine learning algorithms to predict optimal planting and harvesting times based on historical data.",
            "Integrate multiple data sources for comprehensive farm performance analysis and benchmarking."
        ),
        "Crop Rotation" to listOf(
            "Practice crop rotation with deep-rooted plants to break compaction and improve soil drainage.",
            "Implement diverse crop rotations to reduce pest and disease pressure naturally.",
            "Use nitrogen-fixing crops in rotation to reduce synthetic fertilizer requirements.",
            "Plan rotations based on soil health benefits and market opportunities."
        ),
        "Animal Husbandry" to listOf(
            "Implement comprehensive animal health monitoring programs for early disease detection.",
            "Use genetic selection programs to improve herd productivity and disease resistance.",
            "Optimize feeding programs based on animal life stage and production goals.",
            "Implement proper housing and ventilation systems to reduce stress and improve animal welfare."
        ),
        "Weather Monitoring" to listOf(
            "Install on-farm weather stations to collect site-specific meteorological data.",
            "Use real-time weather monitoring to optimize spray timing and field operations.",
            "Implement automated alerts for extreme weather events to protect crops and livestock.",
            "Integrate weather data with irrigation scheduling systems for optimal water management."
        ),
        "Drought Management" to listOf(
            "Implement water conservation practices and drought-resistant crop varieties.",
            "Use deficit irrigation strategies to maintain crop production during water-limited periods.",
            "Develop water storage systems to capture and store precipitation for dry periods.",
            "Monitor soil moisture levels to optimize water use efficiency during drought conditions."
        ),
        "Fertilizer Application" to listOf(
            "Optimize nutrient timing by conducting regular soil tests and adjusting fertilizer applications accordingly.",
            "Use precision fertilizer application technology to reduce waste and environmental impact.",
            "Implement split applications to improve nutrient use efficiency and reduce losses.",
            "Consider slow-release fertilizers to provide consistent nutrition throughout the growing season."
        ),
        "Harvest Planning" to listOf(
            "Use precision harvesting techniques to optimize timing and reduce losses during crop collection.",
            "Invest in storage facilities to take advantage of seasonal price variations and reduce post-harvest losses.",
            "Plan harvest logistics to minimize field traffic and soil compaction.",
            "Implement quality monitoring systems to optimize harvest timing for maximum value."
        )
    )

}
