# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Text, Dict, List
from unicodedata import category

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, ReminderScheduled,SessionStarted,ActionExecuted,EventType
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.types import DomainDict
from datetime import datetime, timedelta
from dateutil import parser
import pytz
import hashlib

from . import Database
from time import sleep
import json
import os

global id
id = None

global rasa_only
rasa_only = False


class ActionSessionStart(Action):
    def name(self) -> Text:
        return "action_session_start"

    async def run(
      self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[EventType]:
        global id
        global rasa_only
        # the session should begin with a `session_started` event
        events = [SessionStarted()]
        amdam_tz = pytz.timezone('Europe/Amsterdam')
        actual_time = datetime.now()
        actual_time_tz = amdam_tz.localize(actual_time, is_dst = True)
        id=tracker.current_state()["sender_id"]
     
        try:
            id = int(id) #if yes this id was send trough ros nose
            Database.initDb(0)       
        except:
            rasa_only = True
            Database.initDb(1)    

        lista = Database.getAllReminder()
        print(len(lista), 'reminder ripristinati')
        for element in lista:
            deadline = element[3]
            time_remind = parser.parse(deadline)-timedelta(seconds = 20)
            if(time_remind < actual_time_tz):
                time = datetime.now()+timedelta(seconds = 2)
                entities = [{'id':element[0],'name':Database.getName(element[0]), 'activity':element[1], 'category':element[2],'deadline': deadline,'expired':True}] # 'time':time
            else: 
                time = time_remind
                entities = [{'id':element[0],'name':Database.getName(element[0]), 'activity':element[1], 'category':element[2],'deadline': deadline,'expired':False}] # 'time':time
            events.append(ReminderScheduled(
                "EXTERNAL_reminder",
                trigger_date_time = time,
                entities = entities,
                kill_on_user_message = False,
            ))
        # an `action_listen` should be added at the end as a user message follows
        events.append(ActionExecuted("action_listen"))

        return events

class actionCreateUser(Action):

    def name(self) -> Text:
        return "action_recognize_user"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global id
        name = tracker.get_slot("name")
        if type(id) != int:
            m = hashlib.sha256()
            id = m.update(str(name.lower()).encode())
            
            m.digest()
            id = m.hexdigest()
     
        if(Database.doesUserExists(id) == False):
            returnedValue = Database.createUser(id,name)
            dispatcher.utter_message(text=f"{name} il tuo account ?? stato correttamente creato!") 
            
        else:
            name = Database.getName(id)
            dispatcher.utter_message(text=f"{name} hai effettuato l'accesso!") 
        return []

class actionAddItem(Action):

    def name(self) -> Text:
        return "action_add_item"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        global id

        associated_name = Database.getName(id)
        activity = tracker.get_slot("activity")
        category = tracker.get_slot("category")
        reminder = tracker.get_slot("reminder")
        time = tracker.get_slot("time")
        if (isinstance(activity,list)):
            activity = ' '.join([str(elem) for elem in activity])
        if (isinstance(category,list)):
            category = ' '.join([str(elem) for elem in category])
        if(time != None and len(time) == 2):
            time = time['to']
        if(Database.doesPossessionExists(id,category)):
            returnedValue= Database.insertItem(id,activity ,category,reminder,time)
            if (returnedValue):  
                text = f"{associated_name}, l'attivita {activity} aggiunta alla categoria {category}" + (f", da completare prima del {time[:10]} alle {time[11:16]}." if time else ".") + ("Te lo ricorder??, non preoccuparti" if reminder else "") 
                if rasa_only:
                    dispatcher.utter_message(text=text) 
                else:
                    dispatcher.utter_message(text=text,json_message={'query':'js'}) 
            else:
                dispatcher.utter_message(text=f"Ops {associated_name}, questa attivita esiste gi??.") 
        else:
            dispatcher.utter_message(text=f"Questa categoria non esisteva, l'ho creata.") 
            actionAddCategory.run(self, dispatcher,tracker,domain)
            actionAddItem.run(self, dispatcher,tracker,domain)
        
        return [SlotSet("activity", None),SlotSet("activity_old", None),SlotSet("activity_new", None),SlotSet("category", None),SlotSet("category_old", None),SlotSet("category_new", None),SlotSet("time",None),SlotSet("activity_status",None)]

class actionRemoveItem(Action):

    def name(self) -> Text:
        return "action_remove_item"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 
      
        global id

        associated_name = Database.getName(id)
        activity = tracker.get_slot("activity")
        category = tracker.get_slot("category")
        time = tracker.get_slot("time")
        if (isinstance(activity,list)):
            activity = ' '.join([str(elem) for elem in activity])
        if (isinstance(category,list)):
            category = ' '.join([str(elem) for elem in category])
        returnedValue = Database.deleteItem(id,activity ,category,time)
        if (returnedValue):
            text = f"{associated_name}, l'attivita {activity} ?? stata rimossa dalla categoria {category} ."
            if rasa_only:
                dispatcher.utter_message(text=text) 
            else:
                dispatcher.utter_message(text=text,json_message={'query':'js'}) 
        else:
            dispatcher.utter_message(text=f"Ops {associated_name}, quest?? attivita non esiste.") 


        return [SlotSet("activity", None),SlotSet("activity_old", None),SlotSet("activity_new", None),SlotSet("category", None),SlotSet("category_old", None),SlotSet("category_new", None),SlotSet("time",None),SlotSet("activity_status",None)]
    
class actionAddCategory(Action):

    def name(self) -> Text:
        return "action_add_category"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 
        
        global id
        
        associated_name = Database.getName(id)
        category = tracker.get_slot("category")
        if (isinstance(category,list)):
            category = ' '.join([str(elem) for elem in category])
        returnedValue = Database.insertCategoryAndPossession(id,category)
        if (returnedValue):  
            text = f"{associated_name}, {category} aggiunta come nuova categoria."
            if rasa_only:
                dispatcher.utter_message(text=text) 
            else:
                dispatcher.utter_message(text=text,json_message={'query':'js'}) 
        else:
            dispatcher.utter_message(text=f"Ops {associated_name}, questa categoria esiste gi??.") 

    
        return [SlotSet("activity", None),SlotSet("activity_old", None),SlotSet("activity_new", None),SlotSet("category", None),SlotSet("category_old", None),SlotSet("category_new", None),SlotSet("time",None),SlotSet("activity_status",None)]
    
class actionRemoveCategory(Action):

    def name(self) -> Text:
        return "action_remove_category"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 
        
        global id
        
        associated_name = Database.getName(id)
        category = tracker.get_slot("category")
        if (isinstance(category,list)):
            category = ' '.join([str(elem) for elem in category])
        returnedValue = Database.deleteCategory(id,category)
        if (returnedValue):  
            text = f"{associated_name}, la categoria {category} ?? stata rimossa."
            if rasa_only:
                dispatcher.utter_message(text=text) 
            else:
                dispatcher.utter_message(text=text,json_message={'query':'js_reload'}) 
        else:
            dispatcher.utter_message(text=f"Ops {associated_name}, questa categoria non esiste.") 

        return [SlotSet("activity", None),SlotSet("activity_old", None),SlotSet("activity_new", None),SlotSet("category", None),SlotSet("category_old", None),SlotSet("category_new", None),SlotSet("time",None),SlotSet("activity_status",None)]

class actionSetStatusActivity(Action):

    def name(self) -> Text:
        return "action_set_status_activity"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        global id
        #aggiunta

        associated_name = Database.getName(id)
        activity = tracker.get_slot("activity")
        category = tracker.get_slot("category")
        activity_status = tracker.get_slot("activity_status")
        time = tracker.get_slot("time")
        if (isinstance(activity,list)):
            activity = ' '.join([str(elem) for elem in activity])
        if (isinstance(category,list)):
            category = ' '.join([str(elem) for elem in category])
        if activity_status == 'completata':
            returnedValue = Database.setItemStatus(id,activity ,category,time,True)
        elif activity_status == 'incompleta':
            returnedValue = Database.setItemStatus(id,activity ,category,time,False)
        else:
            dispatcher.utter_message(text=f"Ops {associated_name}, non ho capito cosa vuoi fare con questa attivita.") 
            return [SlotSet("activity", None),SlotSet("category", None),SlotSet("time",None),SlotSet("activity_status",None)]

        if (returnedValue):  
            text = f"{associated_name}, attivita {activity} in {category} {activity_status} !"
            if rasa_only:
                dispatcher.utter_message(text=text) 
            else:
                dispatcher.utter_message(text=text,json_message={'query':'js'}) 
        else:
            dispatcher.utter_message(text=f"Ops {associated_name}, questa attivita non esiste.") 

        return [SlotSet("activity", None),SlotSet("activity_old", None),SlotSet("activity_new", None),SlotSet("category", None),SlotSet("category_old", None),SlotSet("category_new", None),SlotSet("time",None),SlotSet("activity_status",None)]

class actionSetInComplete(Action):

    def name(self) -> Text:
        return "action_set_uncomplete"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        global id
     
        associated_name = Database.getName(id)
        activity = tracker.get_slot("activity")
        category = tracker.get_slot("category")
        time = tracker.get_slot("time")
        if (isinstance(activity,list)):
            activity = ' '.join([str(elem) for elem in activity])
        if (isinstance(category,list)):
            category = ' '.join([str(elem) for elem in category])
        returnedValue = Database.setItemStatus(id,activity ,category,time,False)

        if (returnedValue):  
            dispatcher.utter_message(text=f"{associated_name}, attivita {activity} in {category} impostata come incompleta.") 
        else:
            dispatcher.utter_message(text=f"Ops {associated_name}, questa attivita non esiste.") 

        return [SlotSet("activity", None),SlotSet("activity_old", None),SlotSet("activity_new", None),SlotSet("category", None),SlotSet("category_old", None),SlotSet("category_new", None),SlotSet("time",None),SlotSet("activity_status",None)]

class showActivities(Action):
    def name(self) -> Text:
        return "action_view_activities"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        global id
        #aggiunta
    
        associated_name = Database.getName(id)
        category = tracker.get_slot("category")
        activity_status = tracker.get_slot("activity_status")
        time = tracker.get_slot("time")
        if (isinstance(category,list)):
            category = ' '.join([str(elem) for elem in category])
        list_of_activity,json = Database.selectItems(id,category, activity_status, time)
        text=associated_name
        if json == None:
            text += f", ecco a te {list_of_activity}." if list_of_activity else " non ci sono attivita per te!"
        else:
            text += f", hai {list_of_activity} attivita." if list_of_activity else " non ci sono attivita per te!"
        dispatcher.utter_message(text=text,json_message=json) 

        return [SlotSet("activity", None),SlotSet("activity_old", None),SlotSet("activity_new", None),SlotSet("category", None),SlotSet("category_old", None),SlotSet("category_new", None),SlotSet("time",None),SlotSet("activity_status",None)]

class showCategories(Action):
    def name(self) -> Text:
        return "action_view_categories"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        global id
        #aggiunta
        
        associated_name = Database.getName(id)
        list_of_categories,json = Database.selectPossessions(id)
        text = associated_name
        if json == None:
            text+=f", ecco a te categorie: {list_of_categories}." if list_of_categories else " non hai alcuna categoria!"
        else:
            text+=f"(, hai {list_of_categories} categorie." if list_of_categories else " non ci sono categorie per te!"

        
        dispatcher.utter_message(text=text,json_message=json) 

        return [SlotSet("activity", None),SlotSet("activity_old", None),SlotSet("activity_new", None),SlotSet("category", None),SlotSet("category_old", None),SlotSet("category_new", None),SlotSet("time",None),SlotSet("activity_status",None)]

class actionModifyCategory(Action):
    def name(self) -> Text:
        return "action_modify_category"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        global id
        
        associated_name = Database.getName(id)
        category_old = tracker.get_slot("category_old")
        if (isinstance(category_old,list)):
            category_old = ' '.join([str(elem) for elem in category_old])
        category_new = tracker.get_slot("category_new")
        if (isinstance(category_new,list)):
            category_new = ' '.join([str(elem) for elem in category_new])
        
        if (Database.doesPossessionExists(id,category_new) == False):
            print(category_new)
            returnedValue = Database.modifyCategory(id, category_old, category_new)
            if (returnedValue):  
                text = f"{associated_name}, categoria {category_old} modificata in {category_new} ."
                if rasa_only:
                    dispatcher.utter_message(text=text) 
                else:
                    dispatcher.utter_message(text=text,json_message={'query':'js_reload'}) 
            else:
                dispatcher.utter_message(text=f"Ops {associated_name} , la categoria {category_old} non esiste.") 
        else:
            dispatcher.utter_message(text=f"Ops {associated_name} , la categoria {category_new} esiste gi??.") 
        
        return [SlotSet("activity", None),SlotSet("activity_old", None),SlotSet("activity_new", None),SlotSet("category", None),SlotSet("category_old", None),SlotSet("category_new", None),SlotSet("time",None),SlotSet("activity_status",None)]

class actionModifyActivity(Action):
    def name(self) -> Text:
        return "action_modify_activity"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        possibleDeadlineErrorFlag=False
        global id


        category_old = tracker.get_slot("category_old")
        activity_old = tracker.get_slot("activity_old")
        activity_new = tracker.get_slot("activity_new")
        category_new = tracker.get_slot("category_new")
        category = tracker.get_slot("category")
        activity = tracker.get_slot("activity")
        time = tracker.get_slot("time")
        if (isinstance(activity_old,list)):
            activity_old = ' '.join([str(elem) for elem in activity_old])
        if (isinstance(activity_new,list)):
            activity_new = ' '.join([str(elem) for elem in activity_new])
        associated_name = Database.getName(id)
        
        if(activity_old!=None):
            act_to_modify = activity_old
        else:
            act_to_modify = activity
        if(category_old!=None):
            cat_to_modify = category_old
        else:
            cat_to_modify = category
        
        if(time != None and len(time) == 2 and not isinstance(time, list)):
            if(time['to'] != None):
                tmp = str(datetime.strptime(time['to'], "%Y-%m-%dT%H:%M:%S.%f%z") - timedelta(days=1)).split(" ")
                timenew = tmp[0] + "T" + (tmp[1])[:-6] + ".000" + (tmp[1])[-6:]
                
            else:
                timenew = time['from'] 
            timeold = time['from']
        elif(isinstance(time, list)):
            timeold = time[0]['from']
            timenew = time[1]
        elif(Database.doesUnfoldingsExists(id,category,activity) and category_new == None and activity_new == None):
            
            timenew = time
            timeold = None
        else:
            possibleDeadlineErrorFlag=True
           
            timenew = time
            timeold = time
        if possibleDeadlineErrorFlag is True and activity_old is None and category_old is None:
            dispatcher.utter_message(text=f"dimmi la deadline precedente e quella nuova nella successiva richiesta per modificare la deadline di un'attivita")
            return [SlotSet("category", None),SlotSet("category_old", None),SlotSet("activity_old", None),SlotSet("category_new", None),SlotSet("activity_new", None),SlotSet("activity", None),SlotSet("time", None)]
    

        if(category_new == None):
            category_new = category
        if(activity_new == None):
            activity_new = activity
      
        if (Database.doesUnfoldingsExists(id,category_new,activity_new,timenew) == False):
            returnedValue = Database.modifyActivity(id, cat_to_modify, act_to_modify, timeold,category_new, activity_new, timenew)
            if (returnedValue):  
                text = f"{associated_name}, l'attivita {act_to_modify} ?? stata modificata"
                if rasa_only:
                    dispatcher.utter_message(text=text) 
                else:
                    dispatcher.utter_message(text=text,json_message={'query':'js'}) 
            else:
                dispatcher.utter_message(text=f"Ops {associated_name} , l'attivita da modificare non esiste.") 
        else:
            dispatcher.utter_message(text=f"Ops {associated_name} l'attivita {activity_new} esiste gi??, non ha senso modificare {act_to_modify}") 
    
        return [SlotSet("activity", None),SlotSet("activity_old", None),SlotSet("activity_new", None),SlotSet("category", None),SlotSet("category_old", None),SlotSet("category_new", None),SlotSet("time",None),SlotSet("activity_status",None)]

class actionSetReminderSlot(Action):
    def name(self) -> Text:
        return "action_set_reminder_slot"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        return[SlotSet("reminder",True)]

class actionCleanCompletedActivities(Action):
    def name(self) -> Text:
        return "action_clean_all_completed"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        global id 
        
        associated_name = Database.getName(id)         
        
        returnedValue = Database.cleanCompletedActivities(id)
        if (returnedValue):  
            text = f"{associated_name}, tutte le tue attivita completate sono state rimosse!"
            if rasa_only:
                dispatcher.utter_message(text=text) 
            else:
                dispatcher.utter_message(text=text,json_message={'query':'js'}) 
        else:
            dispatcher.utter_message(text=f"Ops! {associated_name} qualcosa ?? andato storto! Non riesco a rimuovere tutte le tue attivita completate!") #??
    
        return []

class actionResetSlot(Action):
    def name(self) -> Text:
        return "action_reset_slot"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        
        return [SlotSet("activity_old",None),
        SlotSet("activity",None),
        SlotSet("category_old",None),
        SlotSet("category",None),
        SlotSet("time",None),
        SlotSet("activity_status",None)
        ]

class actionRemindItem(Action):
    def name(self) -> Text:
        return "action_reminder_item"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        global id
        activity = tracker.get_slot("activity")
        category = tracker.get_slot("category")
        reminderSlot = tracker.get_slot("reminder")
        time = tracker.get_slot("time")
        
        associated_name = Database.getName(id) 
        date = datetime.now() + timedelta(seconds = 40)
        if (isinstance(activity,list)):
            activity = ' '.join([str(elem) for elem in activity])
        if (isinstance(category,list)):
            category = ' '.join([str(elem) for elem in category])
        entities = [{'id':id,'name':Database.getName(id), 'activity':activity, 'category':category,'deadline': time,'expired':False}] # 'time':time
        reminder = ReminderScheduled(
            "EXTERNAL_reminder",
            trigger_date_time = date,
            entities = entities,
            kill_on_user_message = False,
        )

        if (Database.doesUnfoldingsExists(id,category,activity,time)):
            
            returnedValue = Database.updateReminder(id,category,activity,time,reminderSlot)
            if (returnedValue):
                text = f"{associated_name}, il reminder per l'attivita ?? stato aggiornato."
                if rasa_only:
                    dispatcher.utter_message(text=text) 
                else:
                    dispatcher.utter_message(text=text,json_message={'query':'js'}) 
            else:
                dispatcher.utter_message(text=f"{associated_name}, ci sono stati dei problemi con l'aggiornamento del reminder!")
        else:
            actionAddItem.run(self,dispatcher,tracker,domain)
        
        #aggiunte per reminder
        return [SlotSet("activity",None), SlotSet("time",None), SlotSet("category",None),SlotSet("reminder",False),reminder]
        
class actionAskCategoryOld(Action):
    def name(self) -> Text:
        return "action_ask_category_old"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        category_old = tracker.get_slot("category_old")
        category = tracker.get_slot("category")
        if(category_old == None and category == None):
            dispatcher.utter_message(text=f"Qual ?? la categoria da modificare?")
            return[SlotSet("requested_slot","category")]
        else:
            dispatcher.utter_message(text=f"Qual ?? la nuova categoria?")
            return[SlotSet("category_old",category),SlotSet("category",None),SlotSet("category_new",None),SlotSet("requested_slot","category")]    
        
class actionAskCategoryNew(Action):
    def name(self) -> Text:
        return "action_ask_category_new"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        category_new = tracker.get_slot("category_new")
        category = tracker.get_slot("category")
        if(category_new == None and category == None):
            dispatcher.utter_message(text=f"Qual ?? la nuova categoria?")
            return[SlotSet("requested_slot","category")]
        else:
            return[SlotSet("category_new",category),SlotSet("category",None),SlotSet("requested_slot",None)]    
        
class actionAskActivityOld(Action):
    def name(self) -> Text:
        return "action_ask_activity_old"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        activity_old = tracker.get_slot("activity_old")
        activity = tracker.get_slot("activity")
        if(activity_old == None and activity == None):
            dispatcher.utter_message(text=f"Qual ?? l'attivita da modificare?")
            return[SlotSet("requested_slot","activity")]
        else:
            dispatcher.utter_message(text=f"Qual ?? la nuova attivita?")
            return[SlotSet("activity_old",activity),SlotSet("activity",None),SlotSet("activity_new",None),SlotSet("requested_slot","activity")]    

class actionAskActivityNew(Action):
    def name(self) -> Text:
        return "action_ask_activity_new"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        activity_new = tracker.get_slot("activity_new")
        activity = tracker.get_slot("activity")
        if(activity_new == None and activity == None):
            dispatcher.utter_message(text=f"Qual ?? la nuova attivita?")
            return[SlotSet("requested_slot","activity")]
        else:
            return[SlotSet("activity_new",activity),SlotSet("activity",None),SlotSet("requested_slot",None)]    
        

# class actionDefaultFallBack(Action):
#     def name(self) -> Text:
#         return "my_action_fallback"
    
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

#         dispatcher.utter_message(text=f"Sorry, I lost my mind! Can you repeat?")    
#         # return [SlotSet("activity_old",None),
#         # SlotSet("activity",None),
#         # SlotSet("category_old",None),
#         # SlotSet("category",None),
#         # SlotSet("time",None),
#         # SlotSet("activity_status",None),
#         # SlotSet("activity_new",None),
#         # SlotSet("category_new",None)]
#         return []


class ActionReactToReminder(Action):
    """Reminds the user to call someone."""

    def name(self) -> Text:
        return "action_react_to_reminder"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        entities = tracker.latest_message.get("entities")[0]
        name = entities['name']
        id_user = entities['id']
        deadline = entities['deadline']
        activity = entities['activity']
        category = entities['category']
        expired = entities['expired']
        print(expired)
        Database.updateReminder(id_user,category, activity, deadline, False)
        if(expired):
            text = f"Hei {name}, il reminder per l'attivita {activity} in {category} ?? scaduto!"
            if rasa_only:
                dispatcher.utter_message(text=text) 
            else:
                dispatcher.utter_message(text=text,json_message={'query':'js'}) 
            print("ti sei scordato ", activity, category)
        else: 
            text = f"Hei {name}, ricordati dell'attivita {activity} in {category} tra cinque minuti!"
            if rasa_only:
                dispatcher.utter_message(text=text) 
            else:
                dispatcher.utter_message(text=text,json_message={'query':'js'}) 
            print("sei ancora in tempo per ricordarti", activity, category)

        #aggiunta per far si che una volta notificato un reminder questo non venga pi?? notificato successivamente
        return []

class ActionRecognizeUser(Action):
    """Return the name of the user"""

    def name(self) -> Text:
        return "action_say_name"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

      
        global id
        
        associated_name = Database.getName(id) 

        dispatcher.utter_message(f"Hey penso tu sia {associated_name}!")

        return []