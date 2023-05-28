from module.base.timer import Timer
from module.base.utils import *
from module.combat.combat import Combat
from module.logger import logger
from module.meta_reward.assets import *
from module.template.assets import TEMPLATE_META_DOCK_RED_DOT
from module.ui.page import page_meta
from module.ui.ui import UI, BACK_ARROW


class MetaReward(Combat, UI):
    def meta_labo_get_sidebar_icon_button(self):
        """
        Get icon button of meta ship.

        Returns:
            list[Button]: Enter button

        Pages:
            in: page_meta
        """
        # Where the click buttons are
        detection_area = (8, 385, 147, 680)
        # Offset inside to avoid clicking on edge
        pad = 2

        list_enter = []
        dots = TEMPLATE_META_DOCK_RED_DOT.match_multi(self.image_crop(detection_area), threshold=5)
        logger.info(f'Possible meta ships found: {len(dots)}')
        for button in dots:
            button = button.move(vector=detection_area[:2])
            enter = button.crop(area=(-129, 3, 3, 42), name='META_SHIP_ENTRANCE')
            enter.area = area_limit(enter.area, detection_area)
            enter._button = area_pad(enter.area, pad)
            list_enter.append(enter)
        return list_enter   

    def meta_labo_sidebar_swipe(self, downward=True, skip_first_screenshot=True):
        """
        Swipe down meta lab sidebar to search for red dots.
        
        
        Args:
            downward (boot): direction of vertical swipe
            skip_first_screenshot (bool):

        Returns:
            bool: If found possible red dot.
        """
        # Where meta dock scroll part is
        detection_area = (8, 392, 233, 680) 
        direction_vector = (0, -200) if downward else (0, 200)

        for _ in range(5):
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            icon = self.meta_labo_get_sidebar_icon_button()
            if len(icon):
                return True
            
            p1, p2 = random_rectangle_vector(
                direction_vector, box=detection_area, random_range=(-30, -30, 30, 30), padding=20)
            self.device.drag(p1, p2, segments=2, shake=(0, 25), point_random=(0, 0, 0, 0), shake_random=(-3, 0, 3, 0))
            self.device.sleep(0.3)
        
        logger.info('No more dossier reward for receiving')
        return False

    def meta_labo_sidebar_icon_button_click(self, skip_first_screenshot=True):
        """
        Click possible dossier ship icon if red dot appears.
        
        Returns:
            bool: If clicked
        """
        timer = Timer(2, count=5)
        clicked = False
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            icon = self.meta_labo_get_sidebar_icon_button()
            if not len(icon):
                break
            if timer.reached():
                logger.info('Click on possible ship icon for further check')
                self.device.click(icon[0])
                # After clicking the icon will enlarge, resulting in original icon to no more match.
                timer.reset()
                clicked = True
                continue
        
        return clicked 

    def meta_reward_notice_appear(self):
        """
        Returns:
            bool: If appear.

        Page:
            in: page_meta
        """
        if self.appear(META_REWARD_NOTICE, threshold=30):
            logger.info('Found meta reward red dot')
            return True
        else:
            logger.info('No meta reward red dot')
            return False

    def meta_reward_enter(self, skip_first_screenshot=True):
        """
        Pages:
            in: page_meta
            out: REWARD_CHECK
        """
        logger.info('Meta reward enter')
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.appear_then_click(REWARD_ENTER, offset=(20, 20), interval=3):
                continue

            # End
            if self.appear(REWARD_CHECK, offset=(20, 20)):
                break

    def meta_reward_receive(self, skip_first_screenshot=True):
        """
        Args:
            skip_first_screenshot:

        Returns:
            bool: If received.

        Pages:
            in: REWARD_CHECK
            out: REWARD_CHECK
        """
        logger.hr('Meta reward receive', level=1)
        confirm_timer = Timer(1, count=3).start()
        received = False
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.appear(REWARD_RECEIVE, offset=(20, 20), interval=3) and REWARD_RECEIVE.match_appear_on(
                    self.device.image):
                self.device.click(REWARD_RECEIVE)
                confirm_timer.reset()
                continue
            if self.handle_popup_confirm('META_REWARD'):
                # Lock new META ships
                confirm_timer.reset()
                continue
            if self.handle_get_items():
                received = True
                confirm_timer.reset()
                continue
            if self.handle_get_ship():
                received = True
                confirm_timer.reset()
                continue

            # End
            if self.appear(REWARD_CHECK, offset=(20, 20)) and \
               self.image_color_count(REWARD_RECEIVE, color=(49, 52, 49), threshold=221, count=400):
                if confirm_timer.reached():
                    break
            else:
                confirm_timer.reset()

        logger.info(f'Meta reward receive finished, received={received}')
        return received
    
    def meta_reward_exit(self, skip_first_screenshot=True):
        """
        Pages:
            in: REWARD_CHECK
            out: page_meta
        """
        logger.info('Meta reward exit')
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.appear(REWARD_CHECK, offset=(20, 20)):
                if self.appear_then_click(BACK_ARROW, offset=(20, 20), interval=3):
                    continue
            
            #ENd
            if self.appear(REWARD_ENTER, offset=(20, 20)):
                return

    def get_meta_reward(self):
        '''
        Wrapper for actual meta reward check and obtain process.

        Pages: page_meta
        '''
        logger.info('Check meta ship reward status')
        if self.meta_reward_notice_appear():
            self.meta_reward_enter()
            self.meta_reward_receive()
            self.meta_reward_exit()
    
    def search_for_dossier_reward(self):
        # Check for red dots on dossier ship lists
        logger.info('Search for dossier ship')
        while self.meta_labo_sidebar_swipe():
            # After clicking the ship icon will enlarge.
            self.meta_labo_sidebar_icon_button_click()
            logger.info('Check dossier ship')
            self.get_meta_reward()

    def has_possible_dossier_reward(self, is_dossier):
        return (is_dossier and "dossier" in self.config.OpsiAshBeacon_AttackMode)

    def run(self, dossier=True):
        # Server check
        if self.config.SERVER in ['cn', 'en', 'jp']:
            pass
        else:
            logger.info(f'MetaReward is not supported in {self.config.SERVER}, please contact server maintainers')
            return

        self.ui_ensure(page_meta)
        
        # OpsiAshBeacon currently does not have a is_dossier property, so needs to do if/else here.
        # Deal current ship reward first.
        logger.info('Check current ship')
        self.get_meta_reward()

        # If dossier beacon is not enabled, or MetaReward is invoked 
        # by AshBeaconAssist, do not need to check dossier 
        if self.has_possible_dossier_reward(is_dossier=dossier):
            # self.search_for_dossier_reward()
            logger.info('Dossier meta reward receiving feature is temporarily disabled by the developer. \nPlease receive it by yourself for the time.')
        else:
            logger.info('MetaReward is called by current beacon, skip dossier reward check')
            return
        