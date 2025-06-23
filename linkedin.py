import time
import math
import random
import os
import utils
import constants
import config
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from utils import prRed, prYellow, prGreen
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
class Linkedin:
    def __init__(self):
        browser = config.browser[0].lower()
        linkedinEmail = config.email
        
        # Configure Chrome/Chromium options
        options = Options()
        
        # Uncomment these for headless/remote execution
        # options.add_argument("--headless=new")
        # options.add_argument("--no-sandbox")
        # options.add_argument("--disable-dev-shm-usage")
        
        # Set browser binary location
        if browser == "chromium":
            options.binary_location = '/snap/bin/chromium'
        else:  # Default to Chrome
            options.binary_location = '/usr/bin/google-chrome'
        
        try:
            # Initialize WebDriver
            service = Service(executable_path='/usr/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=options)
            
            if len(linkedinEmail) > 0:
                self.login_to_linkedin()
                
        except Exception as e:
            prRed(f"Browser initialization failed: {str(e)}")
            raise

    def login_to_linkedin(self):
        self.driver.get("https://www.linkedin.com/login?trk=guest_homepage-basic_nav-header-signin")
        prYellow("Trying to log in to LinkedIn...")
        try:
            self.driver.find_element(By.ID, "username").send_keys(config.email)
            time.sleep(random.uniform(1, 2))
            self.driver.find_element(By.ID, "password").send_keys(config.password)
            time.sleep(random.uniform(1, 2))
            self.driver.find_element(By.XPATH, '//button[@type="submit"]').click()
            time.sleep(random.uniform(3, 15))
        except Exception as e:
            prRed(f"Login error: {str(e)}")

    def generateUrls(self):
        if not os.path.exists('data'):
            os.makedirs('data')
        try:
            with open('data/urlData.txt', 'w', encoding="utf-8") as file:
                linkedinJobLinks = utils.LinkedinUrlGenerate().generateUrlLinks()
                for url in linkedinJobLinks:
                    file.write(url + "\n")
            prGreen("URLs created successfully, the bot will now visit these URLs.")
        except Exception as e:
            prRed(f"Couldn't generate URLs: {str(e)}")

    def linkJobApply(self):
        self.generateUrls()
        countApplied = 0
        countJobs = 0
        urlData = utils.getUrlDataFile()

        for url in urlData:
            print('This is the url to visit:', url.strip())
            self.driver.get(url)
            time.sleep(random.uniform(1, constants.botSpeed))
            
            try:
                totalJobs = self.driver.find_element(By.XPATH, '//small').text
            except:
                prYellow("No matching jobs found")
                continue

            totalPages = utils.jobsToPages(totalJobs)
            urlWords = utils.urlToKeywords(url)
            lineToWrite = f"\nCategory: {urlWords[0]}, Location: {urlWords[1]}, Applying {totalJobs} jobs."
            self.displayWriteResults(lineToWrite)

            for page in range(totalPages):
                currentPageJobs = constants.jobsPerPage * page
                url = url + "&start=" + str(currentPageJobs)
                self.driver.get(url)
                time.sleep(random.uniform(1, constants.botSpeed))

                offersPerPage = self.driver.find_elements(By.XPATH, '//li[@data-occludable-job-id]')
                offerIds = [int(offer.get_attribute("data-occludable-job-id").split(":")[-1]) 
                          for offer in offersPerPage]

                for jobID in offerIds:

                    offerPage = f'https://www.linkedin.com/jobs/view/{jobID}'
                    print('Retrieving job offer page:', offerPage)
                    self.driver.get(offerPage)
                    time.sleep(random.uniform(1, constants.botSpeed))
                    countJobs += 1

                    jobProperties = self.getJobProperties(countJobs)
                    if jobProperties:
                        print(f"Job properties: {jobProperties}")
                    button = self.easyApplyButton()

                    if button:
                        print(f'Easly Apply button found for job: {offerPage}')
                        # button.click()
                        time.sleep(random.uniform(1, constants.botSpeed))
                        countApplied += 1
                        self.handle_application_process(jobProperties, offerPage)
                    else:   
                        lineToWrite = f"{jobProperties} | * Already applied! Job: {offerPage}"
                        self.displayWriteResults(lineToWrite)


            prYellow(f"Category: {urlWords[0]}, {urlWords[1]} applied: {countApplied} jobs out of {countJobs}.")

    def handle_application_process(self, jobProperties, offerPage):
        try:
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 
                                                  "button[aria-label='Submit application']")
            submit_button.click()
            time.sleep(random.uniform(1, constants.botSpeed))
            lineToWrite = f"{jobProperties} | * Applied to this job: {offerPage}"
            self.displayWriteResults(lineToWrite)
        except:
            try:
                self.process_multi_page_application(jobProperties, offerPage)
            except Exception as e:
                lineToWrite = f"{jobProperties} | * Cannot apply to this job! {offerPage}"
                self.displayWriteResults(lineToWrite)

    def process_multi_page_application(self, jobProperties, offerPage):
        continue_button = self.driver.find_element(By.CSS_SELECTOR,
                                                 "button[aria-label='Continue to next step']")
        continue_button.click()
        time.sleep(random.uniform(1, constants.botSpeed))
        
        comPercentage = self.driver.find_element(By.XPATH, 
                                               '//html/body/div[3]/div/div/div[2]/div/div/span').text
        percenNumber = int(comPercentage[0:comPercentage.index("%")])
        result = self.applyProcess(percenNumber, offerPage)
        
        lineToWrite = f"{jobProperties} | {result}"
        self.displayWriteResults(lineToWrite)

    def getJobProperties(self, count):
        properties = {
            'title': self.get_element_text("//h1[contains(@class, 't-bold')]", "jobTitle"),
            'company': self.get_element_text("//div[contains(@class, 'job-details-jobs-unified-top-card__company-name')]//a", "jobCompany"),
            'location': self.get_element_text("(//div[contains(@class, 'job-details-jobs-unified-top-card__primary-description-container')]//span[contains(@class, 'tvm__text')])[1]", "jobLocation"),
            'workplace': self.get_element_text("(//div[contains(@class, 'jobs-unified-top-card')]/div[4]//button/span/strong)[1]", "jobWorkPlace"),
            'posted': self.get_element_text("(//div[contains(@class, 'jobs-unified-top-card')]//strong/span[contains(text(), 'ago')])[1]", "jobPostedDate"),
            'applications': self.get_element_text("(//span[contains(text(), 'applicant')])[1]", "jobApplications")
        }
        return f"{count} | {properties['title']} | {properties['company']} | {properties['location']} | " \
               f"{properties['workplace']} | {properties['posted']} | {properties['applications']}"

    def get_element_text(self, xpath, field_name):
        try:
            return self.driver.find_element(By.XPATH, xpath).get_attribute("innerHTML").strip()
        except Exception as e:
            prYellow(f"Warning in getting {field_name}: {str(e)[:50]}")
            return ""

    # def easyApplyButton(self):
    #     try:
    #         return self.driver.find_element(By.XPATH, '//button[contains(@class, "jobs-apply-button") and span[text()="Easy Apply"]]')
    #     except:
    #         return False

    # 

    def _debug_page_structure(self):
        """Debug the page structure to understand what's available"""
        try:
            print("[DEBUG] Analyzing page structure...")

            # Check current URL
            print(f"[DEBUG] Current URL: {self.driver.current_url}")

            # Look for artdeco-button elements (LinkedIn's main button class)
            artdeco_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'artdeco-button')]")
            print(f"[DEBUG] Found {len(artdeco_buttons)} artdeco-button elements")

            for i, btn in enumerate(artdeco_buttons[:5]):  # Limit to first 5
                try:
                    btn_text = btn.text or btn.get_attribute('textContent') or ''
                    btn_aria = btn.get_attribute('aria-label') or ''
                    btn_class = btn.get_attribute('class') or ''
                    btn_displayed = btn.is_displayed()
                    btn_enabled = btn.is_enabled()

                    print(f"[DEBUG] Artdeco button {i+1}: Text='{btn_text.strip()}', "
                          f"Aria='{btn_aria}', Displayed={btn_displayed}, Enabled={btn_enabled}")
                    print(f"[DEBUG] Classes: {btn_class}")

                    # Check if this looks like an apply button
                    if any(keyword in (btn_text + btn_aria).lower() for keyword in ['apply', 'easy apply', 'submit']):
                        print(f"[DEBUG] ^^^ This button {i+1} looks like an Apply button!")

                except Exception as e:
                    print(f"[DEBUG] Error analyzing artdeco button {i+1}: {e}")

            # Look for any apply-related elements
            apply_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Apply') or contains(@aria-label, 'Apply')]")
            print(f"[DEBUG] Found {len(apply_elements)} elements containing 'Apply'")

            for i, elem in enumerate(apply_elements[:3]):  # Limit to first 3
                try:
                    elem_tag = elem.tag_name
                    elem_text = elem.text or elem.get_attribute('textContent') or ''
                    elem_class = elem.get_attribute('class') or ''
                    elem_displayed = elem.is_displayed()

                    print(f"[DEBUG] Apply element {i+1}: Tag={elem_tag}, Text='{elem_text.strip()}', "
                          f"Displayed={elem_displayed}")

                    if 'artdeco-button' in elem_class:
                        print(f"[DEBUG] ^^^ Apply element {i+1} is an artdeco-button!")

                except Exception as e:
                    print(f"[DEBUG] Error analyzing apply element {i+1}: {e}")

            # Check for specific job application containers
            job_containers = self.driver.find_elements(By.XPATH, 
                "//*[contains(@class, 'jobs-apply') or contains(@class, 'job-actions') or contains(@data-job-id, '')]")
            print(f"[DEBUG] Found {len(job_containers)} job-related containers")

            # Check page state - sometimes LinkedIn loads content dynamically
            page_state = self.driver.execute_script("""
                return {
                    readyState: document.readyState,
                    buttonsLoaded: document.querySelectorAll('button.artdeco-button').length,
                    jobPageLoaded: document.querySelector('[data-job-id]') !== null,
                    hasEasyApplyText: document.body.textContent.includes('Easy Apply')
                };
            """)

            print(f"[DEBUG] Page state: {page_state}")

        except Exception as e:
            print(f"[DEBUG] Error in page structure analysis: {e}")
    
    def easyApplyButton(self):
        """
        Enhanced Easy Apply button handler with viewport and visibility debugging
        """
        try:
            print('Trying to find Easy Apply button...')
            wait = WebDriverWait(self.driver, 15)

            # First, let's debug what's on the page
            self._debug_page_structure()

            # Multiple XPath strategies based on LinkedIn's actual CSS structure
            button_selectors = [
                # Primary selectors based on artdeco-button class structure
                '//button[contains(@class, "artdeco-button") and contains(@aria-label, "Easy Apply")]',
                '//button[contains(@class, "artdeco-button") and .//span[contains(text(), "Easy Apply")]]',
                '//button[contains(@class, "artdeco-button") and contains(text(), "Easy Apply")]',

                # Jobs-specific selectors
                '//button[contains(@class, "jobs-apply-button")]',
                '//div[contains(@class, "jobs-apply-button")]//button[contains(@class, "artdeco-button")]',

                # Fallback selectors
                '//button[contains(@aria-label, "Easy Apply")]',
                '//button[contains(text(), "Easy Apply")]',

                # More specific artdeco combinations
                '//button[contains(@class, "artdeco-button--primary") and contains(., "Easy Apply")]',
                '//button[contains(@class, "artdeco-button") and contains(@class, "jobs-apply-button")]',

                # Generic artdeco button with Apply text
                '//button[contains(@class, "artdeco-button") and contains(., "Apply")]',

                # Container-based searches
                '//div[contains(@class, "jobs-apply")]//button[contains(@class, "artdeco-button")]',
                '//div[@data-job-id]//button[contains(@class, "artdeco-button") and contains(., "Apply")]',

                # Link-based (sometimes Easy Apply is a link)
                '//a[contains(@class, "artdeco-button") and contains(@href, "easy-apply")]',
                '//a[contains(@class, "artdeco-button") and contains(@aria-label, "Easy Apply")]'
            ]

            button = None
            successful_selector = None
            all_found_buttons = []

            # Try each selector and collect all found buttons
            for i, selector in enumerate(button_selectors):
                try:
                    print(f"[EasyApplyButton] Trying selector {i+1}: {selector}")
                    buttons = self.driver.find_elements(By.XPATH, selector)

                    if buttons:
                        print(f"[EasyApplyButton] Found {len(buttons)} button(s) with selector {i+1}")
                        for j, btn in enumerate(buttons):
                            try:
                                btn_info = {
                                    'element': btn,
                                    'selector': selector,
                                    'index': j,
                                    'text': btn.text or btn.get_attribute('textContent') or '',
                                    'aria_label': btn.get_attribute('aria-label') or '',
                                    'class': btn.get_attribute('class') or '',
                                    'displayed': btn.is_displayed(),
                                    'enabled': btn.is_enabled(),
                                    'location': btn.location,
                                    'size': btn.size
                                }
                                all_found_buttons.append(btn_info)
                                print(f"[EasyApplyButton] Button {j+1}: Text='{btn_info['text']}', "
                                      f"Aria='{btn_info['aria_label']}', Displayed={btn_info['displayed']}, "
                                      f"Enabled={btn_info['enabled']}")
                            except Exception as btn_error:
                                print(f"[EasyApplyButton] Error analyzing button {j+1}: {btn_error}")

                except Exception as e:
                    print(f"[EasyApplyButton] Selector {i+1} failed: {e}")
                    continue
                
            if not all_found_buttons:
                print("[EasyApplyButton] No buttons found with any selector")
                return False

            # Find the best button to use (prioritize visible Easy Apply buttons)
            best_button = self._select_best_button(all_found_buttons)

            if not best_button:
                print("[EasyApplyButton] No suitable button found")
                return False

            button = best_button['element']
            successful_selector = best_button['selector']
            print(f"[EasyApplyButton] Selected button: {best_button['text']} | {best_button['aria_label']}")

            # Handle hidden buttons by making them visible
            if not best_button['displayed']:
                print("[EasyApplyButton] Button is hidden, attempting to make it visible...")
                success = self._handle_hidden_button(button)
                if not success:
                    return False

            # Enhanced scrolling with multiple strategies
            scroll_success = self._enhanced_scroll_to_element(button)
            if not scroll_success:
                print("[EasyApplyButton] Failed to scroll to button properly")
                # Continue anyway, might still work

            # Wait for any animations or transitions to complete
            time.sleep(2)

            # Try to make button clickable if it's not
            if not button.is_enabled():
                print("[EasyApplyButton] Button is disabled, trying to enable...")
                try:
                    self.driver.execute_script("arguments[0].disabled = false;", button)
                    self.driver.execute_script("arguments[0].removeAttribute('disabled');", button)
                except Exception as e:
                    print(f"[EasyApplyButton] Could not enable button: {e}")

            # Multiple click strategies with enhanced error handling
            click_strategies = [
                ("ActionChains move and click", self._action_chains_click),
                ("JavaScript click with event", self._js_click_with_event),
                ("Force visible and click", self._force_visible_click),
                ("Coordinate click", self._coordinate_click),
                ("Standard click", lambda btn: btn.click()),
                ("Simple JavaScript click", lambda btn: self.driver.execute_script("arguments[0].click();", btn))
            ]

            # Try each click strategy
            for strategy_name, click_func in click_strategies:
                try:
                    print(f"[EasyApplyButton] Trying {strategy_name}...")
                    click_func(button)
                    time.sleep(3)  # Wait longer for modal to appear

                    # Verify if Easy Apply modal opened
                    if self._verify_easy_apply_modal():
                        print(f"[EasyApplyButton] Success with {strategy_name}!")
                        return True
                    else:
                        print(f"[EasyApplyButton] {strategy_name} clicked but no modal appeared")

                except Exception as e:
                    print(f"[EasyApplyButton] {strategy_name} failed: {e}")
                    continue
                
            print("[EasyApplyButton] All click strategies failed")
            return False
        
        except Exception as e:
            print(f"[EasyApplyButton] Critical error: {e}")
            return False

    def applyProcess(self, percentage, offerPage):
        applyPages = math.floor(100 / percentage)
        result = ""
        try:
            for _ in range(applyPages - 2):
                self.driver.find_element(By.CSS_SELECTOR,
                                       "button[aria-label='Continue to next step']").click()
                time.sleep(random.uniform(1, constants.botSpeed))

            self.driver.find_element(By.CSS_SELECTOR,
                                   "button[aria-label='Review your application']").click()
            time.sleep(random.uniform(1, constants.botSpeed))

            if config.followCompanies is False:
                self.driver.find_element(By.CSS_SELECTOR,
                                       "label[for='follow-company-checkbox']").click()
                time.sleep(random.uniform(1, constants.botSpeed))

            self.driver.find_element(By.CSS_SELECTOR,
                                   "button[aria-label='Submit application']").click()
            time.sleep(random.uniform(1, constants.botSpeed))

            result = f"* Applied to this job: {offerPage}"
        except:
            result = f"* {applyPages} pages, couldn't apply! Extra info needed: {offerPage}"
        return result

    def displayWriteResults(self, lineToWrite: str):
        try:
            print(lineToWrite)
            utils.writeResults(lineToWrite)
        except Exception as e:
            prRed(f"Error in DisplayWriteResults: {str(e)}")

    #__________--------------------------------------------------___________________



    def _select_best_button(self, buttons):
        """Select the best button from found buttons"""
        try:
            # Priority order: visible Easy Apply > hidden Easy Apply > visible Apply > any Apply
            easy_apply_visible = [b for b in buttons if 'Easy Apply' in (b['text'] + b['aria_label']) and b['displayed']]
            easy_apply_hidden = [b for b in buttons if 'Easy Apply' in (b['text'] + b['aria_label']) and not b['displayed']]
            apply_visible = [b for b in buttons if 'Apply' in (b['text'] + b['aria_label']) and b['displayed']]
            apply_any = [b for b in buttons if 'Apply' in (b['text'] + b['aria_label'])]

            for button_list in [easy_apply_visible, easy_apply_hidden, apply_visible, apply_any]:
                if button_list:
                    return button_list[0]

            return buttons[0] if buttons else None

        except Exception as e:
            print(f"[EasyApplyButton] Error selecting best button: {e}")
            return buttons[0] if buttons else None

    def _handle_hidden_button(self, button):
        """Attempt to make hidden button visible using LinkedIn's CSS structure"""
        try:
            print("[EasyApplyButton] Attempting to make hidden button visible...")
            
            # LinkedIn-specific CSS fixes based on artdeco-button structure
            self.driver.execute_script("""
                var button = arguments[0];
                
                // Reset display properties
                button.style.display = 'inline-flex';  // artdeco-button uses inline-flex
                button.style.visibility = 'visible';
                button.style.opacity = '1';
                button.style.height = 'auto';
                button.style.width = 'auto';
                button.style.maxWidth = '480px';  // Based on CSS max-width
                button.style.minWidth = '6.4rem';
                
                // Ensure proper positioning
                button.style.position = 'relative';
                button.style.zIndex = '1000';
                
                // Remove any hidden/disabled attributes
                button.removeAttribute('hidden');
                button.removeAttribute('disabled');
                button.disabled = false;
                
                // Ensure cursor is pointer (from CSS)
                button.style.cursor = 'pointer';
                
                // Apply artdeco-button styling
                button.style.alignItems = 'center';
                button.style.justifyContent = 'center';
                button.style.boxSizing = 'border-box';
                button.style.fontWeight = '600';
                button.style.textAlign = 'center';
                button.style.verticalAlign = 'middle';
                button.style.overflow = 'hidden';
                
                // Handle parent containers that might be hiding the button
                var parent = button.parentElement;
                var attempts = 0;
                while (parent && attempts < 5) {
                    parent.style.display = 'block';
                    parent.style.visibility = 'visible';
                    parent.style.opacity = '1';
                    parent.style.overflow = 'visible';
                    parent = parent.parentElement;
                    attempts++;
                }
                
            """, button)
            
            time.sleep(1.5)  # Wait for CSS changes to take effect
            
            # Additional check - make sure button is not covered by other elements
            self.driver.execute_script("""
                var button = arguments[0];
                var rect = button.getBoundingClientRect();
                var centerX = rect.left + rect.width / 2;
                var centerY = rect.top + rect.height / 2;
                var elementAtPoint = document.elementFromPoint(centerX, centerY);
                
                // If another element is covering our button, try to bring button to front
                if (elementAtPoint !== button && !button.contains(elementAtPoint)) {
                    button.style.zIndex = '9999';
                    button.style.position = 'relative';
                }
            """, button)
            
            if button.is_displayed():
                print("[EasyApplyButton] Successfully made button visible")
                return True
            else:
                print("[EasyApplyButton] Button still hidden after visibility attempts")
                # Try one more approach - clone and replace
                return self._clone_and_replace_button(button)
                
        except Exception as e:
            print(f"[EasyApplyButton] Error making button visible: {e}")
            return False
    
    def _clone_and_replace_button(self, button):
        """Last resort: clone the button and make it visible"""
        try:
            print("[EasyApplyButton] Attempting to clone and replace hidden button...")
            
            clone_success = self.driver.execute_script("""
                var originalButton = arguments[0];
                
                // Create a clone of the button
                var clonedButton = originalButton.cloneNode(true);
                
                // Make the clone visible and functional
                clonedButton.style.display = 'inline-flex';
                clonedButton.style.visibility = 'visible';
                clonedButton.style.opacity = '1';
                clonedButton.style.position = 'relative';
                clonedButton.style.zIndex = '10000';
                clonedButton.style.backgroundColor = '#0a66c2';  // LinkedIn blue
                clonedButton.style.color = 'white';
                clonedButton.style.padding = '8px 16px';
                clonedButton.style.borderRadius = '2px';
                clonedButton.style.border = 'none';
                clonedButton.style.cursor = 'pointer';
                clonedButton.id = 'easy-apply-clone-' + Date.now();
                
                // Copy all event listeners by recreating the click functionality
                clonedButton.addEventListener('click', function(e) {
                    // Trigger click on original button
                    originalButton.click();
                });
                
                // Insert the clone after the original
                originalButton.parentNode.insertBefore(clonedButton, originalButton.nextSibling);
                
                return clonedButton.id;
            """, button)
            
            if clone_success:
                # Find the cloned button
                cloned_button = self.driver.find_element(By.ID, clone_success)
                if cloned_button.is_displayed():
                    print("[EasyApplyButton] Successfully created visible clone")
                    return True
                    
            return False
            
        except Exception as e:
            print(f"[EasyApplyButton] Clone and replace failed: {e}")
            return False
    
    def _enhanced_scroll_to_element(self, element):
        """Enhanced scrolling with multiple strategies"""
        try:
            strategies = [
                # Strategy 1: Smooth scroll to center
                lambda: self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element),
                # Strategy 2: Immediate scroll to center
                lambda: self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", element),
                # Strategy 3: Scroll to top of element
                lambda: self.driver.execute_script("arguments[0].scrollIntoView(true);", element),
                # Strategy 4: Manual coordinate scroll
                lambda: self._scroll_to_coordinates(element)
            ]
            
            for i, strategy in enumerate(strategies):
                try:
                    print(f"[EasyApplyButton] Scroll strategy {i+1}")
                    strategy()
                    time.sleep(1.5)
                    
                    # Verify element is in viewport
                    in_viewport = self.driver.execute_script("""
                        var rect = arguments[0].getBoundingClientRect();
                        var viewHeight = Math.max(document.documentElement.clientHeight, window.innerHeight);
                        var viewWidth = Math.max(document.documentElement.clientWidth, window.innerWidth);
                        return (rect.top >= 0 && rect.left >= 0 && 
                                rect.bottom <= viewHeight && rect.right <= viewWidth);
                    """, element)
                    
                    if in_viewport:
                        print(f"[EasyApplyButton] Scroll strategy {i+1} successful")
                        return True
                        
                except Exception as e:
                    print(f"[EasyApplyButton] Scroll strategy {i+1} failed: {e}")
                    continue
                    
            return False
            
        except Exception as e:
            print(f"[EasyApplyButton] Enhanced scroll failed: {e}")
            return False
    
    def _scroll_to_coordinates(self, element):
        """Scroll to element using coordinates"""
        try:
            location = element.location
            size = element.size
            
            # Calculate center coordinates
            center_x = location['x'] + size['width'] // 2
            center_y = location['y'] + size['height'] // 2
            
            # Scroll to center coordinates
            self.driver.execute_script(f"window.scrollTo({center_x - window.innerWidth//2}, {center_y - window.innerHeight//2});")
            
        except Exception as e:
            print(f"[EasyApplyButton] Coordinate scroll failed: {e}")
    
    def _action_chains_click(self, element):
        """Enhanced ActionChains click"""
        actions = ActionChains(self.driver)
        actions.move_to_element(element).pause(0.5).click().perform()
    
    def _js_click_with_event(self, element):
        """JavaScript click with proper event simulation"""
        self.driver.execute_script("""
            var element = arguments[0];
            var event = new MouseEvent('click', {
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: element.getBoundingClientRect().left + element.offsetWidth / 2,
                clientY: element.getBoundingClientRect().top + element.offsetHeight / 2
            });
            element.dispatchEvent(event);
        """, element)
    
    def _force_visible_click(self, element):
        """Force element to be visible and clickable, then click"""
        self.driver.execute_script("""
            var element = arguments[0];
            element.style.display = 'block';
            element.style.visibility = 'visible';
            element.style.opacity = '1';
            element.style.pointerEvents = 'auto';
            element.click();
        """, element)
    
    def _coordinate_click(self, element):
        """Click at specific coordinates"""
        location = element.location
        size = element.size
        
        # Calculate center coordinates
        center_x = location['x'] + size['width'] // 2
        center_y = location['y'] + size['height'] // 2
        
        actions = ActionChains(self.driver)
        actions.move_by_offset(center_x, center_y).click().perform()
        # Reset to avoid affecting future actions
        actions.move_by_offset(-center_x, -center_y).perform()
    
    def _verify_easy_apply_modal(self):
        """
        Enhanced verification if the Easy Apply modal has opened
        """
        try:
            print("[EasyApplyButton] Verifying if Easy Apply modal opened...")
            
            modal_selectors = [
                # Updated selectors for current LinkedIn
                '//div[contains(@class, "jobs-easy-apply-modal")]',
                '//div[@role="dialog"]',
                '//div[contains(@class, "artdeco-modal")]',
                '//div[contains(@class, "jobs-easy-apply-content")]',
                '//div[contains(@class, "jobs-easy-apply")]',
                '//form[contains(@class, "jobs-easy-apply")]',
                # Check for modal backdrop
                '//div[contains(@class, "artdeco-modal-overlay")]',
                # Check for specific Easy Apply text in modal
                '//*[text()[contains(., "Easy Apply")] and ancestor::div[@role="dialog"]]'
            ]
            
            wait = WebDriverWait(self.driver, 8)
            
            for i, selector in enumerate(modal_selectors):
                try:
                    modal = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    if modal.is_displayed():
                        print(f"[EasyApplyButton] Modal verified with selector {i+1}: {selector}")
                        
                        # Additional verification - check modal content
                        modal_text = modal.text or modal.get_attribute('textContent') or ''
                        print(f"[EasyApplyButton] Modal text preview: {modal_text[:100]}...")
                        
                        # Look for specific Easy Apply indicators
                        easy_apply_indicators = [
                            'Easy Apply', 'Submit application', 'Your application',
                            'Upload resume', 'Contact info', 'Additional Questions'
                        ]
                        
                        if any(indicator in modal_text for indicator in easy_apply_indicators):
                            print("[EasyApplyButton] Confirmed Easy Apply modal content")
                            return True
                        else:
                            print("[EasyApplyButton] Modal found but content doesn't match Easy Apply")
                            continue
                            
                except Exception as e:
                    continue
                    
            # Fallback: Check if URL changed (sometimes indicates modal opened)
            current_url = self.driver.current_url
            if 'easy-apply' in current_url.lower():
                print("[EasyApplyButton] Easy Apply detected in URL")
                return True
                
            print("[EasyApplyButton] No Easy Apply modal detected")
            return False
            
        except Exception as e:
            print(f"[EasyApplyButton] Modal verification failed: {e}")
            return False
    
    # Additional helper method to handle different job states
    def check_job_application_status(self):
        """
        Check if the job has already been applied to or if it's an external application
        """
        try:
            # Check for "Applied" status
            applied_elements = self.driver.find_elements(By.XPATH, 
                '//span[contains(text(), "Applied") or contains(text(), "Application submitted")]')
            
            if applied_elements:
                print("[JobStatus] Job already applied to")
                return "already_applied"
            
            # Check for external application
            external_elements = self.driver.find_elements(By.XPATH, 
                '//button[contains(text(), "Apply on company website") or contains(@aria-label, "Apply on company website")]')
            
            if external_elements:
                print("[JobStatus] External application required")
                return "external_application"
            
            # Check for Easy Apply availability
            easy_apply_elements = self.driver.find_elements(By.XPATH, 
                '//button[contains(text(), "Easy Apply") or contains(@aria-label, "Easy Apply")]')
            
            if easy_apply_elements:
                print("[JobStatus] Easy Apply available")
                return "easy_apply_available"
            
            print("[JobStatus] Unknown job status")
            return "unknown"
            
        except Exception as e:
            print(f"[JobStatus] Error checking job status: {e}")
            return "error"

if __name__ == "__main__":
    start = time.time()
    try:
        Linkedin().linkJobApply()
    except Exception as e:
        prRed(f"Application error: {str(e)}")
    finally:
        end = time.time()
        prYellow(f"--- Runtime: {round((end - start)/60, 2)} minutes ---")
        try:
            Linkedin().driver.quit()
        except Exception as e:
            prRed(f"Error closing the browser: {str(e)}")
        prGreen("Browser closed successfully.")
        prGreen("Thank you for using the Linkedin Application Bot!")








#__________________________________________________________________________________________________________________








