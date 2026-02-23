// Service Name Change Detector
// Detects posts that mention renamed AWS services

class ServiceNameDetector {
    constructor() {
        this.services = [];
        this.loaded = false;
    }

    async init() {
        try {
            // Load the service mapping JSON
            const response = await fetch('euc-service-name-mapping.json');
            const data = await response.json();
            this.services = data.services || [];
            this.loaded = true;
            console.log(`Service name detector loaded ${this.services.length} services`);
        } catch (error) {
            console.warn('Could not load service name mappings:', error);
            this.loaded = false;
        }
    }

    // Check if a post mentions a renamed service
    detectRenamedService(post) {
        if (!this.loaded || !post) return null;

        const searchText = `${post.title || ''} ${post.content || ''} ${post.tags || ''}`.toLowerCase();

        for (const service of this.services) {
            // Only check services that have been renamed
            if (!service.previous_names || service.previous_names.length === 0) continue;
            if (!service.rename_date) continue;

            // Check if any previous name is mentioned
            for (const oldName of service.previous_names) {
                if (searchText.includes(oldName.toLowerCase())) {
                    return {
                        oldName: oldName,
                        newName: service.current_name,
                        renameDate: service.rename_date
                    };
                }
            }
        }

        return null;
    }
}

// Global instance
window.serviceNameDetector = new ServiceNameDetector();
