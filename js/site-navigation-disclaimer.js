/**
 * Site Navigation Disclaimer
 * Shows a disclaimer modal when navigating between RIA site and ETF site
 */

(function() {
    'use strict';

    // Check if we're on RIA site (/) or ETF site (/etfs/)
    function isRIASite() {
        const path = window.location.pathname;
        return path === '/' || path === '/index.html' || (!path.startsWith('/etfs/') && !path.startsWith('/red/'));
    }

    function isETFSite() {
        const path = window.location.pathname;
        return path.startsWith('/etfs/') || path.startsWith('/red/');
    }

    // Check if link navigates between RIA and ETF sites
    function isCrossSiteNavigation(href) {
        if (!href) return false;
        
        // Skip anchor links (same page navigation)
        if (href.startsWith('#')) return false;
        
        // Skip external links
        if (href.startsWith('http://') || href.startsWith('https://')) {
            try {
                const url = new URL(href);
                // Only check if it's same origin
                if (url.origin !== window.location.origin) return false;
            } catch (e) {
                return false;
            }
        }
        
        // Handle relative and absolute URLs
        let targetPath;
        try {
            const url = new URL(href, window.location.origin);
            targetPath = url.pathname;
        } catch (e) {
            return false;
        }
        
        // Get current site type
        const currentIsRIA = isRIASite();
        const currentIsETF = isETFSite();
        
        // Determine target site type
        const targetIsETF = targetPath.startsWith('/etfs/') || targetPath.startsWith('/red/');
        const targetIsRIA = !targetIsETF && (targetPath === '/' || targetPath === '/index.html' || 
                           (!targetPath.startsWith('/etfs/') && !targetPath.startsWith('/red/')));
        
        // Only show disclaimer when actually crossing between different site types
        // Case 1: Currently on RIA site, navigating to ETF site
        if (currentIsRIA && targetIsETF) {
            return true;
        }
        
        // Case 2: Currently on ETF site, navigating to RIA site
        if (currentIsETF && targetIsRIA) {
            return true;
        }
        
        // All other cases: same-site navigation (RIA->RIA or ETF->ETF) - don't show disclaimer
        return false;
    }

    // Create and show disclaimer modal
    function showDisclaimerModal(targetUrl, linkText) {
        // Check if modal already exists
        let modal = document.getElementById('site-navigation-disclaimer-modal');
        if (modal) {
            modal.remove();
        }

        // Determine which site we're going to
        const goingToETF = targetUrl.includes('/etfs/') || targetUrl.includes('/red/');
        const fromSite = isRIASite() ? 'Investment Advisory Services' : 'ETF Products';
        const toSite = goingToETF ? 'ETF Products' : 'Investment Advisory Services';

        // Create modal
        modal = document.createElement('div');
        modal.id = 'site-navigation-disclaimer-modal';
        modal.innerHTML = `
            <div class="disclaimer-overlay" style="
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            ">
                <div class="disclaimer-modal" style="
                    background: white;
                    border-radius: 12px;
                    max-width: 600px;
                    width: 100%;
                    max-height: 90vh;
                    overflow-y: auto;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                    animation: slideIn 0.3s ease-out;
                ">
                    <div style="padding: 2rem;">
                        <div style="
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            margin-bottom: 1.5rem;
                            padding-bottom: 1rem;
                            border-bottom: 2px solid #e8e0e0;
                        ">
                            <h2 style="
                                font-size: 1.5rem;
                                font-weight: 700;
                                color: #1a0a0a;
                                margin: 0;
                            ">Important Notice</h2>
                            <button id="disclaimer-close-btn" style="
                                background: none;
                                border: none;
                                font-size: 1.5rem;
                                color: #6b7280;
                                cursor: pointer;
                                padding: 0;
                                width: 32px;
                                height: 32px;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                border-radius: 4px;
                                transition: all 0.2s;
                            " onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='none'">
                                ×
                            </button>
                        </div>
                        
                        <div style="margin-bottom: 1.5rem;">
                            <p style="
                                color: #374151;
                                line-height: 1.6;
                                margin-bottom: 1rem;
                                font-size: 1rem;
                            ">
                                You are navigating from our <strong>${fromSite}</strong> section to our <strong>${toSite}</strong> section.
                            </p>
                            
                            <div style="
                                background: #fff3f3;
                                border-left: 4px solid #8b0000;
                                padding: 1.25rem;
                                border-radius: 6px;
                                margin-bottom: 1rem;
                            ">
                                <p style="
                                    color: #1a0a0a;
                                    line-height: 1.7;
                                    margin: 0;
                                    font-size: 0.95rem;
                                    font-weight: 500;
                                ">
                                    <strong>Regulatory Disclosure:</strong> Diamond Asset Management (DAM) provides both investment advisory services and manages exchange-traded funds (ETFs). These are separate business divisions with distinct regulatory requirements and disclosures.
                                </p>
                            </div>
                            
                            <ul style="
                                color: #374151;
                                line-height: 1.8;
                                margin: 1rem 0;
                                padding-left: 1.5rem;
                                font-size: 0.95rem;
                            ">
                                <li style="margin-bottom: 0.5rem;">Investment advisory services and ETF products are subject to different regulations and disclosures.</li>
                                <li style="margin-bottom: 0.5rem;">Information on one section may not apply to the other.</li>
                                <li style="margin-bottom: 0.5rem;">Please review all relevant disclosures and documentation for each service or product.</li>
                                <li>Past performance does not guarantee future results.</li>
                            </ul>
                            
                            <p style="
                                color: #6b7280;
                                line-height: 1.6;
                                margin-top: 1rem;
                                font-size: 0.875rem;
                                font-style: italic;
                            ">
                                By proceeding, you acknowledge that you understand the distinction between our advisory services and ETF products.
                            </p>
                        </div>
                        
                        <div style="
                            display: flex;
                            gap: 1rem;
                            justify-content: flex-end;
                            margin-top: 2rem;
                            padding-top: 1.5rem;
                            border-top: 1px solid #e8e0e0;
                        ">
                            <button id="disclaimer-cancel-btn" style="
                                background: white;
                                color: #8b0000;
                                border: 2px solid #8b0000;
                                padding: 0.75rem 1.5rem;
                                border-radius: 6px;
                                font-weight: 600;
                                cursor: pointer;
                                transition: all 0.2s;
                                font-size: 0.95rem;
                            " onmouseover="this.style.background='#faf8f8'" onmouseout="this.style.background='white'">
                                Cancel
                            </button>
                            <button id="disclaimer-proceed-btn" style="
                                background: #8b0000;
                                color: white;
                                border: none;
                                padding: 0.75rem 1.5rem;
                                border-radius: 6px;
                                font-weight: 600;
                                cursor: pointer;
                                transition: all 0.2s;
                                font-size: 0.95rem;
                            " onmouseover="this.style.background='#a00000'" onmouseout="this.style.background='#8b0000'">
                                Proceed
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: scale(0.95) translateY(-20px);
                }
                to {
                    opacity: 1;
                    transform: scale(1) translateY(0);
                }
            }
        `;
        document.head.appendChild(style);

        document.body.appendChild(modal);
        document.body.style.overflow = 'hidden'; // Prevent background scrolling

        // Event handlers
        const closeModal = () => {
            modal.remove();
            document.body.style.overflow = '';
        };

        const proceed = () => {
            closeModal();
            window.location.href = targetUrl;
        };

        document.getElementById('disclaimer-close-btn').addEventListener('click', closeModal);
        document.getElementById('disclaimer-cancel-btn').addEventListener('click', closeModal);
        document.getElementById('disclaimer-proceed-btn').addEventListener('click', proceed);

        // Close on overlay click
        modal.querySelector('.disclaimer-overlay').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                closeModal();
            }
        });

        // Close on Escape key
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
    }

    // Intercept link clicks
    function interceptLinks() {
        document.addEventListener('click', function(e) {
            let link = e.target;
            
            // Find the link element (might be nested)
            while (link && link.tagName !== 'A') {
                link = link.parentElement;
            }
            
            if (!link || !link.href) return;

            const href = link.getAttribute('href');
            if (!href) return;

            // Check if this is a cross-site navigation
            if (isCrossSiteNavigation(href)) {
                // If we're on the ETF site, only show disclaimer for DAM button
                if (isETFSite()) {
                    const linkText = link.textContent.trim() || '';
                    // Only show for links that say "DAM" (case insensitive)
                    if (!linkText.toLowerCase().includes('dam')) {
                        // Not the DAM button, allow normal navigation
                        return;
                    }
                }
                
                e.preventDefault();
                e.stopPropagation();
                
                const linkText = link.textContent.trim() || 'this link';
                showDisclaimerModal(href, linkText);
            }
        }, true); // Use capture phase to catch events early
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', interceptLinks);
    } else {
        interceptLinks();
    }
})();
