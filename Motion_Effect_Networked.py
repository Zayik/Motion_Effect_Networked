# OBS-Studio python scripts
# Copyright (C) 2020 Zayik

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Motion_Effect_Networked.py
# This is a python script inspired by the Motion Effect Plugin. 
# This script is inteded to communicate with a networked device such as 
# the Stream Deck using my CommandSender plugin for it. 
# This is currently a beta. 

import obspython as obs
from typing import List
from pprint import pprint
import re
import threading
import socket
import time
import math
import logging 

source_name = ""
visible = True
animationCount = 0
source_item = None
settings = []
props = obs.obs_properties_create()

VARIATION_POSITION = (1<<0)
VARIATION_SIZE = (1<<1)
VARIATION_BOTH = VARIATION_POSITION | VARIATION_SIZE
VARIATION_POSITION_FREE = (1<<2)
VARIATION_SIZE_FREE = (1<<3)
VARIATION_POSITION_FREE_ALL = (1<<4)

MOVEMENT_SPEED = (1<<0)
MOVEMENT_DURATION = (1<<1)
MOVEMENT_QUICKEST = MOVEMENT_SPEED | MOVEMENT_DURATION

DefaultUpdatePerSecond = 60
UpdatesPerSecond = 60
TickFactor = DefaultUpdatePerSecond / UpdatesPerSecond

UpdateRateMs = int(1000/UpdatesPerSecond)

Animations = [] # type: List[Animation] 

source_pos = obs.vec2()

class ServerClass:
    def __init__(self):
        self.address = "localhost"
        self.port = "12345"

        self.addressStorage = "addressStorage"
        self.portStorage = "portStorage"
        self.thread = None

        self.run = False
        # If Ping time exceed
        self.lastPingTime = time.clock()
        self.closeIfNoPingInXSeconds = 8
        self.threadId = 0
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socketClosed = True

    def checkServer(self):
        if self.thread == None:
            self.createServerThread()
        elif not self.run:
            self.createServerThread()

    def createServerThread(self):
        print("Checking the Server")
        self.run = True
        self.thread = threading.Thread(target=self.serverThread, args=(Animations,))
        self.thread.start()
        self.threadId = self.thread.ident
        print('Creating thread with name %s, id %s' % (self.thread.getName(), self.thread.ident))
            
    def serverThread(self, animations):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Attempt to bind the socket to an address and port.
        try:
            self.serverSocket.bind((Server.address, Server.port))
        except socket.error:
            # If we come across an error, shut down the server thread so another one can be made.
            self.run = False
        print("Starting the Server")
        self.serverSocket.settimeout(5)
        while self.run:
            try:
                data, addr = self.serverSocket.recvfrom(1024)
                decodedData = "".join(map(chr, data))
                print("Message: ", decodedData)
                if decodedData != None and decodedData != "":
                    ProcessCommand(decodedData, animations)
            except socket.timeout: # fail after 1 second of no activity
                test = 0
            except:
                print("Socket failed to receive. Socket could be closed or program is existing.")
                self.run = False
            if(time.clock() - self.lastPingTime) >= self.closeIfNoPingInXSeconds:
                print("Closing server due to ping not received.")
                self.run = False
                break
        if not self.socketClosed:
            self.socketClosed = True
            self.serverSocket.shutdown(socket.SHUT_RDWR)
            self.serverSocket.close()
        print("Server Thread Exiting.")
        
    def forceCloseServerSocket(self):
        self.socketClosed = True
        self.serverSocket.shutdown(socket.SHUT_RDWR)
        self.serverSocket.close()
        self.run = False
        print("serverSocket: %s" % (self.serverSocket))


class VariationType:
    def __init__(self):
        self.Name = "variation_type"
        self.Type = "VariationType"
        self.Position = "Position"
        self.Size = "Size"
        self.PositionAndSize = "PositionAndSize"
        self.PositionFree = "PositionFree"
        self.SizeFree = "SizeFree"
        self.PositionFreeAll = "PositionFreeAll"

class MovementType:
    def __init__(self):
        self.Name = "movement_type"
        self.Type = "MovementType"
        self.Speed = "Speed"
        self.Duration = "Duration"
        self.Quickest = "Quickest"        

Movement = MovementType()

class DirectionType:
    def __init__(self):
        self.Type = "DirectionType"
        self.Up = "⇑ Up"
        self.Down = "⇓ Down"
        self.Left = "⇐ Left"
        self.Right = "⇒ Right"
        self.Up_Left = "⇖ Up_Left"
        self.Up_Right = "⇗ Up_Right"
        self.Down_Left = "⇙ Down_Left"
        self.Down_Right = "⇘ Down_Right"

        self.UP_INDEX = 0
        self.DOWN_INDEX = 1
        self.LEFT_INDEX = 2
        self.RIGHT_INDEX = 3
        self.UP_LEFT_INDEX = 4
        self.UP_RIGHT_INDEX = 5
        self.DOWN_LEFT_INDEX = 6
        self.DOWN_RIGHT_INDEX = 7

class Animation:
  def __init__(self, animationIndex):
    self.animationIndex = animationIndex
    
    self.customStartingSetting = False
    self.startingX = 0
    self.startingY = 0
    self.startingWidth = 0
    self.startingHeight = 0
    
    self.destinationX = 0
    self.destinationY = 0
    self.destinationWidth = 0
    self.destinationHheight = 0
    self.variationType = Variation.Position

    self.movementType = Movement.Duration
    self.duration = 3
    self.posSpeed = 10

    self.changeSizeInPlace = False

    self.posDirection = Direction.RIGHT_INDEX
    self.command = ""
    self.stopCommand = ""

    self.customStartingSettingStorage = "customStartingSetting" + str(animationIndex)
    self.startingXStorage = "startingX" + str(animationIndex)
    self.startingYStorage = "startingY" + str(animationIndex)
    self.startingWidthStorage = "startingWidth" + str(animationIndex)
    self.startingHeightStorage = "startingHeight" + str(animationIndex)
    
    self.destinationXStorage = "destinationX" + str(animationIndex)
    self.destinationYStorage = "destinationY" + str(animationIndex)
    self.destinationWidthStorage = "destinationWidth" + str(animationIndex)
    self.destinationHeightStorage = "destinationHeight" + str(animationIndex)
    self.variationTypeStorage = "variation_type" + str(animationIndex)
    self.movementTypeStorage = "movementTypeStorage" + str(animationIndex)
    self.posSpeedStorage = "posSpeedStorage" + str(animationIndex)
    self.durationStorage = "durationStorage" + str(animationIndex)
    self.posDirectionStorage = "posDirectionStorage" + str(animationIndex)
    self.setDestinationStorage = "setDestinationStorage" + str(animationIndex)
    self.changeSizeInPlaceStorage = "changeSizeInPlaceStorage" + str(animationIndex)
    self.commandStorage = "command" + str(animationIndex)
    self.stopCommandStorage = "stopCommand" + str(animationIndex)

class SourceClass:
    def __init__(self):
        self.pos = obs.vec2()
        # This is needed to store the remainder values since position is integer only.
        self.posRemainder = obs.vec2()
        self.size = obs.vec2()
        self.scale = obs.vec2()
        self.targetPos = obs.vec2()
        self.targetSize = obs.vec2()
        self.targetScale = obs.vec2()
        self.posSpeed = 1
        self.processingAnimation = False
        self.forceX = 0
        self.forceY = 0
        self.forceW = 0
        self.forceH = 0

    def GetXAndYForce(self, movementType, duration):
        self.forceX = 0
        self.forceY = 0

        distance = math.sqrt(math.pow(self.targetPos.x - self.pos.x, 2) + math.pow(self.targetPos.y - self.pos.y, 2))
        print("Distance: ", distance, ", Duration: ", duration)
        if duration == 0:
            durationBasedSpeed = distance
        else:
            durationBasedSpeed = distance / duration
        print("Duration based speed: ", durationBasedSpeed, ", movementType: ", movementType)
        if movementType == MOVEMENT_DURATION:
            self.posSpeed = durationBasedSpeed
        if movementType == MOVEMENT_QUICKEST:
            if self.posSpeed < durationBasedSpeed:
                self.posSpeed = durationBasedSpeed

        if distance != 0:
            self.forceX = self.posSpeed/distance * (self.targetPos.x - self.pos.x)
            self.forceY = self.posSpeed/distance * (self.targetPos.y - self.pos.y)

    def GetXAndYScaleForce(self, duration):
        self.forceW = 0
        self.forceH = 0

        print("Scale: scale.x: ", self.scale.x, ", scale.y: ", self.scale.y, ", targetScale.x: ", self.targetScale.x, ", targetScale.y: ", self.targetScale.y)
        if duration == 0:
            self.forceW = self.targetScale.x - self.scale.x
            self.forceH = self.targetScale.y - self.scale.y
        else:
            self.forceW = (self.targetScale.x - self.scale.x) / duration
            self.forceH = (self.targetScale.y - self.scale.y) / duration
            print("Forces: W: ", self.forceW, "  -  H: ", self.forceH)

        
       

Variation = VariationType()
Direction = DirectionType()
Server = ServerClass()
Source = SourceClass()

def ProcessCommand(command, animations):
    # Find the animation with the corresponding command then do stuff based on it.
    global Animations
    for i in range(animationCount):
        #print("Command: ", command, "  -  Variation Type: ", Animations[i].variationType)
        if Animations[i].command == command:
            Source.processingAnimation = True
            ProcessAnimation(Animations[i])
            print("Command ", command, " available and now executing!")
        elif ((Animations[i].variationType == VARIATION_POSITION_FREE or Animations[i].variationType == VARIATION_SIZE_FREE) and Animations[i].stopCommand == command):
            print("Stop Command ", command, " available and now executing!")
            Source.targetPos = Source.pos
            Source.processingAnimation = False
        elif Animations[i].variationType == VARIATION_POSITION_FREE_ALL:
            commandSuffix = Animations[i].command
            stopCommandSuffix = Animations[i].stopCommand
            if command.endswith(commandSuffix):
                direction = command[:-len(commandSuffix)]
                if direction == "Up":
                    Animations[i].posDirection = Direction.UP_INDEX
                elif direction == "Down":
                    Animations[i].posDirection = Direction.DOWN_INDEX
                elif direction == "Left":
                    Animations[i].posDirection = Direction.LEFT_INDEX
                elif direction == "Right":
                    Animations[i].posDirection = Direction.RIGHT_INDEX

                elif direction == "UpLeft" or direction == "Up_Left":
                    Animations[i].posDirection = Direction.UP_LEFT_INDEX
                elif direction == "UpRight" or direction == "Up_Right":
                    Animations[i].posDirection = Direction.UP_RIGHT_INDEX
                elif direction == "DownLeft" or direction == "Down_Left":
                    Animations[i].posDirection = Direction.DOWN_LEFT_INDEX
                elif direction == "DownRight" or direction == "Down_Right":
                    Animations[i].posDirection = Direction.DOWN_RIGHT_INDEX
                Source.processingAnimation = True
                ProcessAnimation(Animations[i])
            elif command.endswith(stopCommandSuffix):
                Source.targetPos = Source.pos
                Source.processingAnimation = False

def ProcessAnimation(animation):
    if animation.variationType == VARIATION_POSITION_FREE or animation.variationType == VARIATION_POSITION_FREE_ALL:
        ProcessPositionFreeAnimation(animation)
        Source.GetXAndYForce(animation.movementType, animation.duration)
    elif animation.variationType == VARIATION_POSITION:
        InitializeSource(animation, True, False)
        Source.GetXAndYForce(animation.movementType, animation.duration)
    elif animation.variationType == VARIATION_SIZE or animation.variationType == VARIATION_BOTH:
        InitializeSource(animation, animation.variationType == VARIATION_BOTH, True)

        if animation.changeSizeInPlace:
            Source.targetPos.x -= int(math.floor((Source.targetSize.x - Source.size.x) / 2))
            Source.targetPos.y -= int(math.floor((Source.targetSize.y - Source.size.y) / 2))

        if animation.variationType == VARIATION_BOTH or animation.changeSizeInPlace:
            Source.GetXAndYForce(MOVEMENT_DURATION, animation.duration)
        Source.GetXAndYScaleForce(animation.duration)
        
def InitializeSource(animation, positionSpecified, sizeSpecified):
    scene_item = findSceneItem(source_name)
    print("scene_item: ", scene_item)
    if scene_item != None:
        posV = obs.vec2()
        scaleV = obs.vec2()

        obs.obs_sceneitem_get_pos(scene_item, posV)
        obs.obs_sceneitem_get_scale(scene_item, scaleV) 
        Source.scale.x = scaleV.x
        Source.scale.y = scaleV.y
        width, height = calculateSize(scene_item, Source.scale.x, Source.scale.y)
        Source.pos = posV
        Source.size.x = width
        Source.size.y = height
        
        Source.posSpeed = animation.posSpeed
        if positionSpecified:
            Source.targetPos.x = animation.destinationX
            Source.targetPos.y = animation.destinationY
        else:
            Source.targetPos.x = posV.x
            Source.targetPos.y = posV.y

        if sizeSpecified:
            Source.targetSize.x = animation.destinationWidth
            Source.targetSize.y = animation.destinationHeight
            scaleV.x, scaleV.y = calculateNewScale(scene_item, Source.targetSize.x, Source.targetSize.y)
            Source.targetScale.x = scaleV.x
            Source.targetScale.y = scaleV.y
        else:
            Source.targetSize.x = Source.size.x
            Source.targetSize.y = Source.size.y
            Source.targetScale.x = Source.scale.x
            Source.targetScale.y = Source.scale.y
        

        
    
def ProcessPositionFreeAnimation(animation):
    InitializeSource(animation, True, False)

    # Determine direction.
    if animation.posDirection == Direction.UP_INDEX:
        Source.targetPos.y -= 5000
        Source.targetPos.x = Source.pos.x
    elif animation.posDirection == Direction.DOWN_INDEX:
        Source.targetPos.y += 5000
        Source.targetPos.x = Source.pos.x
    elif animation.posDirection == Direction.RIGHT_INDEX:
        Source.targetPos.x += 5000
        Source.targetPos.y = Source.pos.y
    elif animation.posDirection == Direction.LEFT_INDEX:
        Source.targetPos.x -= 5000
        Source.targetPos.y = Source.pos.y

    elif animation.posDirection == Direction.DOWN_LEFT_INDEX:
        Source.targetPos.x = Source.pos.x - 5000
        Source.targetPos.y = Source.pos.y + 5000
    elif animation.posDirection == Direction.DOWN_RIGHT_INDEX:
        Source.targetPos.x = Source.pos.x + 5000
        Source.targetPos.y = Source.pos.y + 5000
    elif animation.posDirection == Direction.UP_RIGHT_INDEX:
        Source.targetPos.x = Source.pos.x + 5000
        Source.targetPos.y = Source.pos.y - 5000
    elif animation.posDirection == Direction.UP_LEFT_INDEX:
        Source.targetPos.x = Source.pos.x - 5000
        Source.targetPos.y = Source.pos.y - 5000

def SetDestinationPositionAndSize(props, p):
    global source_name
    global Animations

    # Base the index off of the name since callbacks don't work well.
    name = obs.obs_property_name(p)
    indexStr = re.sub("[^0-9]", "", name)
    
    animationIndex = int(indexStr)
    sceneItem = findSceneItem(source_name)
    
    posV = obs.vec2()
    scaleV = obs.vec2()
    obs.obs_sceneitem_get_pos(sceneItem, posV)
    obs.obs_sceneitem_get_scale(sceneItem, scaleV) 

    width, height = calculateSize(sceneItem, scaleV.x, scaleV.y)
    Animations[animationIndex].destinationX = posV.x
    Animations[animationIndex].destinationY = posV.y
    Animations[animationIndex].destinationWidth = width
    Animations[animationIndex].destinationHeight = height
    obs.obs_data_set_int(settings, Animations[animationIndex].destinationXStorage, (int)(Animations[animationIndex].destinationX))
    obs.obs_data_set_int(settings, Animations[animationIndex].destinationYStorage, (int)(Animations[animationIndex].destinationY))
    obs.obs_data_set_int(settings, Animations[animationIndex].destinationWidthStorage, (int)(Animations[animationIndex].destinationWidth))
    obs.obs_data_set_int(settings, Animations[animationIndex].destinationHeightStorage, (int)(Animations[animationIndex].destinationHeight))

def adjustCameraTick():
    global source_item
    global source_name
    global source_pos
    global UpdateRateMs

    scene_item = findSceneItem(source_name)
    if scene_item != None:
        posV = obs.vec2()
        scaleV = obs.vec2()

        obs.obs_sceneitem_get_pos(scene_item, posV)
        obs.obs_sceneitem_get_scale(scene_item, scaleV) 
        width, height = calculateSize(scene_item, Source.scale.x, Source.scale.y)
        Source.pos = posV
        Source.size.x = width
        Source.size.y = height

        # Do not control any aspect of the source if no animation is currently playing. 
        if not Source.processingAnimation:
            return

        if Source.pos.x != Source.targetPos.x:
            fractionX = (float(Source.forceX) / float(UpdatesPerSecond)) + Source.posRemainder.x
            integerX = int(math.floor(fractionX))
            Source.posRemainder.x = fractionX - integerX
            Source.pos.x += integerX
            if (integerX > 0 and Source.pos.x > Source.targetPos.x) or (integerX < 0 and Source.pos.x < Source.targetPos.x):
                Source.pos.x = Source.targetPos.x

        if Source.pos.y != Source.targetPos.y:
            fractionY = (Source.forceY / UpdatesPerSecond) + Source.posRemainder.y
            integerY = int(math.floor(fractionY))
            Source.posRemainder.y = fractionY - integerY
            Source.pos.y += integerY
            if (integerY > 0 and Source.pos.y > Source.targetPos.y) or (integerY < 0 and Source.pos.y < Source.targetPos.y):
                Source.pos.y = Source.targetPos.y

        if Source.scale.x != Source.targetScale.x:
            fractionX = (float(Source.forceW) / float(UpdatesPerSecond))
            Source.scale.x += fractionX
            if (fractionX > 0 and Source.scale.x > Source.targetScale.x) or (fractionX < 0 and Source.scale.x < Source.targetScale.x):
                Source.scale.x = Source.targetScale.x

        if Source.scale.y != Source.targetScale.y:
            fractionY = (float(Source.forceH) / float(UpdatesPerSecond))
            Source.scale.y += fractionY
            if (fractionY > 0 and Source.scale.y > Source.targetScale.y) or (fractionY < 0 and Source.scale.y < Source.targetScale.y):
                Source.scale.y = Source.targetScale.y

        if Source.pos.x == Source.targetPos.x and Source.pos.y == Source.targetPos.y and Source.scale.x == Source.targetScale.x and Source.scale.y == Source.targetScale.y:
            Source.processingAnimation = False

        # Update the position and size of the source based on speed/
        obs.obs_sceneitem_set_pos(scene_item, Source.pos)
        obs.obs_sceneitem_set_scale(scene_item, Source.scale)

def findCurrentSceneName():
    try:
        sceneSource = obs.obs_frontend_get_current_scene()
    except Exception as e: 
        print(e)
    return obs.obs_source_get_name(sceneSource)

def findSceneItem(source_name):
    src = obs.obs_get_source_by_name(findCurrentSceneName())
    if src:
        scene = obs.obs_scene_from_source(src)
        obs.obs_source_release(src)
        if scene:
            sceneItem = obs.obs_scene_find_source(scene, source_name)
            return sceneItem


def calculateSize(scene_item, scaleX, scaleY):
    src = obs.obs_sceneitem_get_source(scene_item)
    baseWidth = obs.obs_source_get_base_width(src)
    baseHeight = obs.obs_source_get_base_height(src)

    return (int)(baseWidth * scaleX), (int)(baseHeight * scaleY)

def calculateNewScale(item, width, height):
    src = obs.obs_sceneitem_get_source(item)

    baseWidth = obs.obs_source_get_base_width(src)
    baseHeight = obs.obs_source_get_base_height(src)
    print("width: ", width, ", height: ", height)
    print("baseWidth: ", baseWidth, ", baseHeight: ", baseHeight)
    return (width / baseWidth), ( height / baseHeight)

def script_properties():
    """
    Called to define user properties associated with the script. These
    properties are used to define how to show settings properties to a user.
    """
    global Animations
    global props
    props = obs.obs_properties_create()
    ######################################################################
    ## Allow user to select which Video source to create an animation for.
    ######################################################################
    p = obs.obs_properties_add_list(props, "source", "Video Source",
                                    obs.OBS_COMBO_TYPE_EDITABLE,
                                    obs.OBS_COMBO_FORMAT_STRING)
    sources = obs.obs_enum_sources()
    if sources is not None:
        for source in sources:
            source_id = obs.obs_source_get_id(source)
            if source_id == "dshow_input":
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(p, name, name)

        obs.source_list_release(sources)
    ######################################################################

    ######################################################################
    ## Display Server Settings
    ######################################################################
    obs.obs_properties_add_text(props, Server.addressStorage, "Address", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(props, Server.portStorage,"Port",0, 99999, 1)
    ######################################################################

    obs.obs_properties_add_int(props,
                               "animationCount",
                               "Animations (Reload scripts to take effect)",
                               1,
                               25,
                               1)
    obs.obs_property_set_modified_callback("animationCount", properties_set_vis)

    customStartingProperties = []
    variationProperties = []
    setDestinationValuesButtons = []
    # For each command, do the following: 
    for i in range(animationCount):
        index = i
        obs.obs_properties_add_text(props, "Blocker"+str(i), "------------------Animation " + str(i) + "-------------------", obs.OBS_TEXT_DEFAULT)

        property_list = obs.obs_properties_add_list(props, Animations[i].variationTypeStorage, Variation.Type, obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT)
        obs.obs_property_list_add_int(property_list, Variation.Position, VARIATION_POSITION)
        obs.obs_property_list_add_int(property_list, Variation.Size, VARIATION_SIZE)
        obs.obs_property_list_add_int(property_list, Variation.PositionAndSize, VARIATION_POSITION | VARIATION_SIZE)
        obs.obs_property_list_add_int(property_list, Variation.PositionFree, VARIATION_POSITION_FREE)
        obs.obs_property_list_add_int(property_list, Variation.PositionFreeAll, VARIATION_POSITION_FREE_ALL)
        obs.obs_property_list_add_int(property_list, Variation.SizeFree, VARIATION_SIZE_FREE)
        variationProperties.append(property_list)

        customStartingProperties.append(obs.obs_properties_add_bool(props, Animations[i].customStartingSettingStorage, "Custom Starting Setting"))
        
        obs.obs_property_set_modified_callback(customStartingProperties[index], properties_set_vis)
        obs.obs_property_set_modified_callback(variationProperties[index], properties_set_vis)
        obs.obs_property_set_modified_callback(customStartingProperties[index], properties_set_vis)

        setDestinationValuesButtons.append(obs.obs_properties_add_button(props, Animations[i].setDestinationStorage, "Populate Destination Position And Size (Reload Script To See Change)", SetDestinationPositionAndSize))        

        obs.obs_properties_add_int(props, Animations[i].startingXStorage,"Starting X",-8192, 8192, 1)
        obs.obs_properties_add_int(props, Animations[i].startingYStorage,"Starting Y",-8192, 8192, 1)
        obs.obs_properties_add_int(props, Animations[i].destinationXStorage,"Destination X",-8192, 8192, 1)
        obs.obs_properties_add_int(props, Animations[i].destinationYStorage,"Destination Y",-8192, 8192, 1)
        

        # Handle movement type:
        movement_property_list = obs.obs_properties_add_list(props, Animations[i].movementTypeStorage, Movement.Type, obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT)
        obs.obs_property_list_add_int(movement_property_list, Movement.Speed, MOVEMENT_SPEED)
        obs.obs_property_list_add_int(movement_property_list, Movement.Duration, MOVEMENT_DURATION)
        obs.obs_property_list_add_int(movement_property_list, Movement.Quickest, MOVEMENT_QUICKEST)

        obs.obs_properties_add_int(props, Animations[i].durationStorage,"Duration (seconds)",0, 8192, 1)
        obs.obs_properties_add_int(props, Animations[i].posSpeedStorage,"Position Speed (Pixels per second)",1, 8192, 1)

        # Handle pos speed direction
        direction_list = obs.obs_properties_add_list(props, Animations[i].posDirectionStorage, Direction.Type, obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT)
        obs.obs_property_list_add_int(direction_list, Direction.Up, Direction.UP_INDEX)
        obs.obs_property_list_add_int(direction_list, Direction.Down, Direction.DOWN_INDEX)
        obs.obs_property_list_add_int(direction_list, Direction.Left, Direction.LEFT_INDEX)
        obs.obs_property_list_add_int(direction_list, Direction.Right, Direction.RIGHT_INDEX)
        
        obs.obs_property_list_add_int(direction_list, Direction.Up_Left, Direction.UP_LEFT_INDEX)
        obs.obs_property_list_add_int(direction_list, Direction.Up_Right, Direction.UP_RIGHT_INDEX)
        obs.obs_property_list_add_int(direction_list, Direction.Down_Left, Direction.DOWN_LEFT_INDEX)
        obs.obs_property_list_add_int(direction_list, Direction.Down_Right, Direction.DOWN_RIGHT_INDEX)

        obs.obs_properties_add_int(props, Animations[i].startingWidthStorage,"Starting Width",-8192, 8192, 1)
        obs.obs_properties_add_int(props, Animations[i].startingHeightStorage,"Starting Height",-8192, 8192, 1)
        obs.obs_properties_add_int(props, Animations[i].destinationWidthStorage,"Destination Width",-8192, 8192, 1)
        obs.obs_properties_add_int(props, Animations[i].destinationHeightStorage,"Destination Height",-8192, 8192, 1)

        obs.obs_properties_add_bool(props, Animations[i].changeSizeInPlaceStorage,"Change Size In Place")

        obs.obs_properties_add_text(props, Animations[i].commandStorage, "Command", obs.OBS_TEXT_DEFAULT)
        obs.obs_properties_add_text(props, Animations[i].stopCommandStorage, "Stop Command", obs.OBS_TEXT_DEFAULT)
        animationProperties_set_vis(props, Animations[i], Animations[i].variationType, Animations[i].customStartingSetting)
    return props

def properties_set_vis(props, p, settings):
    name = obs.obs_property_name(p)
    indexStr = re.sub("[^0-9]", "", name)
    
    animationIndex = int(indexStr)

    showStartingProperties = obs.obs_data_get_bool(settings, Animations[animationIndex].customStartingSettingStorage)
    variationType = obs.obs_data_get_int(settings, Animations[animationIndex].variationTypeStorage)
    animationProperties_set_vis(props, Animations[animationIndex], variationType, showStartingProperties)
    return True

def animationProperties_set_vis(props, animation, variationType, showStartingProperties):
    global settings

    setDestinationProperty = obs.obs_properties_get(props, animation.setDestinationStorage)
    customStartingSettingsProperty = obs.obs_properties_get(props, animation.customStartingSettingStorage)
    posDirectionProperty = obs.obs_properties_get(props, animation.posDirectionStorage)
    commandProperty = obs.obs_properties_get(props, animation.commandStorage)
    stopCommandProperty = obs.obs_properties_get(props, animation.stopCommandStorage)

    startingXProperty = obs.obs_properties_get(props, animation.startingXStorage)
    startingYProperty = obs.obs_properties_get(props, animation.startingYStorage)
    destinationXProperty = obs.obs_properties_get(props, animation.destinationXStorage)
    destinationYProperty = obs.obs_properties_get(props, animation.destinationYStorage)
    posSpeedProperty = obs.obs_properties_get(props, animation.posSpeedStorage)
    movementTypeProperty = obs.obs_properties_get(props, animation.movementTypeStorage)

    changeSizeInPlaceProperty = obs.obs_properties_get(props, animation.changeSizeInPlaceStorage)

    if variationType == VARIATION_POSITION or variationType == VARIATION_BOTH: 
        obs.obs_property_set_visible(startingXProperty, showStartingProperties)
        obs.obs_property_set_visible(startingYProperty, showStartingProperties)
        obs.obs_property_set_visible(destinationXProperty, True)
        obs.obs_property_set_visible(destinationYProperty, True)
        obs.obs_property_set_visible(posSpeedProperty, True)
    else:
        obs.obs_property_set_visible(startingXProperty, False)
        obs.obs_property_set_visible(startingYProperty, False)
        obs.obs_property_set_visible(destinationXProperty, False)
        obs.obs_property_set_visible(destinationYProperty, False)
        obs.obs_property_set_visible(posSpeedProperty, False)

    startingWidthProperty = obs.obs_properties_get(props, animation.startingWidthStorage)
    startingHeightProperty = obs.obs_properties_get(props, animation.startingHeightStorage)
    destinationWidthProperty = obs.obs_properties_get(props, animation.destinationWidthStorage)
    destinationHeightProperty = obs.obs_properties_get(props, animation.destinationHeightStorage)

    if variationType == VARIATION_SIZE or variationType == VARIATION_BOTH: 
        obs.obs_property_set_visible(startingWidthProperty, showStartingProperties)
        obs.obs_property_set_visible(startingHeightProperty, showStartingProperties)
        obs.obs_property_set_visible(destinationWidthProperty, True)
        obs.obs_property_set_visible(destinationHeightProperty, True)
        obs.obs_property_set_visible(posSpeedProperty, False)
        obs.obs_property_set_visible(movementTypeProperty, False)
    else:
        obs.obs_property_set_visible(startingWidthProperty, False)
        obs.obs_property_set_visible(startingHeightProperty, False)
        obs.obs_property_set_visible(destinationWidthProperty, False)
        obs.obs_property_set_visible(destinationHeightProperty, False)
        obs.obs_property_set_visible(movementTypeProperty, True)

    if variationType == VARIATION_POSITION_FREE or variationType == VARIATION_SIZE_FREE or variationType == VARIATION_POSITION_FREE_ALL:
        obs.obs_property_set_visible(setDestinationProperty, False)
        obs.obs_property_set_visible(customStartingSettingsProperty, False)
        obs.obs_property_set_visible(stopCommandProperty, True)
    else:
        obs.obs_property_set_visible(setDestinationProperty, True)
        obs.obs_property_set_visible(customStartingSettingsProperty, True)
        obs.obs_property_set_visible(stopCommandProperty, False)

    if variationType == VARIATION_POSITION_FREE:
        obs.obs_property_set_visible(posSpeedProperty, True)
        obs.obs_property_set_visible(posDirectionProperty, True)
    else:
        obs.obs_property_set_visible(posDirectionProperty, False)

    if variationType == VARIATION_POSITION_FREE_ALL:
        obs.obs_property_set_visible(posSpeedProperty, True)
    
    if variationType == VARIATION_SIZE:
        obs.obs_property_set_visible(changeSizeInPlaceProperty, True)
    else:
        obs.obs_property_set_visible(changeSizeInPlaceProperty, False)

def check_Server():
    print("Check Server")
    Server.checkServer()

def ping_Server():
    print("Ping Server")
    Server.lastPingTime = time.clock()

def script_update(updatedSettings):
    """
    Called when the script’s settings (if any) have been changed by the user.
    """
    global source_name
    global animationCount
    global Server
    global Animations
    global settings
    global props

    print("Script Update Called")

    try:
        settings = updatedSettings

        Animations.clear()
        source_name = obs.obs_data_get_string(settings, "source")
        animationCount = obs.obs_data_get_int(settings, "animationCount")
        Server.address = obs.obs_data_get_string(settings, Server.addressStorage)
        Server.port = obs.obs_data_get_int(settings, Server.portStorage)

        for i in range(animationCount):
            # Create animations based on stored stuff.
            animation = Animation(i)
            
            animation.variationType = obs.obs_data_get_int(settings, animation.variationTypeStorage)
            animation.customStartingSetting = obs.obs_data_get_bool(settings, animation.customStartingSettingStorage)

            # Get Starting Position and Scale
            animation.startingX = obs.obs_data_get_int(settings, animation.startingXStorage)
            animation.startingY = obs.obs_data_get_int(settings, animation.startingYStorage)
            animation.startingWidth = obs.obs_data_get_int(settings, animation.startingWidthStorage)
            animation.startingHeight = obs.obs_data_get_int(settings, animation.startingHeightStorage)
            
            animation.movementType = obs.obs_data_get_int(settings, animation.movementTypeStorage)
            animation.duration = obs.obs_data_get_int(settings, animation.durationStorage)
            animation.posSpeed = obs.obs_data_get_int(settings, animation.posSpeedStorage)

            # Get Destination Position and Scale
            animation.destinationX = obs.obs_data_get_int(settings, animation.destinationXStorage)
            animation.destinationY = obs.obs_data_get_int(settings, animation.destinationYStorage)
            animation.destinationWidth = obs.obs_data_get_int(settings, animation.destinationWidthStorage)
            animation.destinationHeight = obs.obs_data_get_int(settings, animation.destinationHeightStorage)

            animation.posDirection = obs.obs_data_get_int(settings, animation.posDirectionStorage)
            animation.changeSizeInPlace = obs.obs_data_get_bool(settings, animation.changeSizeInPlaceStorage)
            animation.command = obs.obs_data_get_string(settings, animation.commandStorage)
            animation.stopCommand = obs.obs_data_get_string(settings, animation.stopCommandStorage)
            Animations.append(animation)

        #only remove/add events if our server thread is failing. 
        serverThreadFound = False
        main_thread = threading.current_thread()
        for t in threading.enumerate():
            if t is main_thread or t.getName().startswith('Dummy'):
                print('Main/Dummy Thread with name %s, id %s' % (t.getName(), t.ident))
                continue
            print('Thread with name %s, id %s' % (t.getName(), t.ident))
            Server.threadId = t.ident
            serverThreadFound = True
            break

        #if not serverThreadFound:
        # By default the server will close itself within 5 seconds of this flag being set.
        Server.run = False
        obs.timer_remove(adjustCameraTick)
        obs.timer_remove(DelayedTimerAddition)
        obs.timer_add(DelayedTimerAddition, 8000)
        
        obs.timer_remove(check_Server)
        obs.timer_add(check_Server, 10000)
        obs.timer_remove(adjustCameraTick)
        obs.timer_add(adjustCameraTick, UpdateRateMs)
        
        obs.timer_remove(ping_Server)
        # # Time is in ms.
        obs.timer_add(ping_Server, (Server.closeIfNoPingInXSeconds-1)*1000)

        obs.obs_frontend_remove_event_callback(shutdownServer)
        obs.obs_frontend_add_event_callback(shutdownServer)

    except Exception as e: 
        print(e)

def shutdownServer(data):
    print("Shutdown")
    print("Data: %s" % (data))
    if data == 17:
        Server.run = False
        Server.forceCloseServerSocket()
        obs.timer_remove(ping_Server)
        obs.timer_remove(check_Server)
        obs.timer_remove(adjustCameraTick)
        obs.timer_remove(DelayedTimerAddition)

        main_thread = threading.current_thread()
        for t in threading.enumerate():
            if t is main_thread or t.getName().startswith('Dummy'):
                print('Main/Dummy Thread with name %s, id %s' % (t.getName(), t.ident))
                continue
            print('Thread with name %s, id %s' % (t.getName(), t.ident))
            #t.join()


def DelayedTimerAddition():
    obs.timer_remove(adjustCameraTick)
    obs.timer_add(adjustCameraTick, UpdateRateMs)
    obs.timer_remove(DelayedTimerAddition)