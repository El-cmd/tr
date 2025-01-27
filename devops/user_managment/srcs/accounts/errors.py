class RelationError(Exception):
    """
    Raised when relation update is incoherent or invalid
    """
    base_mess = "Relation error"
    message = 'not specified'
    
    def __init__(self, message=None):
        if message is None:
            message = self.message
        self.message = message
        super(RelationError, self).__init__(f'{self.base_mess}: {self.message}')
        
        
class UnknownRelationError(RelationError):
    """
    Raised when a string can not be converted into a valid relation
    """
    message = 'unable to convert {relation_str} into RelationsType'
    
    def __init__(self, relation_str):
        message = self.message.format(relation_str=relation_str)
        super().__init__(message)
        
class BlockedTwice(RelationError):
    message = 'you are trying to block the same user twice, why so much hate?'

class NotBlocked(RelationError):
    message = 'you did not block that user, or already unblocked them'

class AlreadyRequested(RelationError):
    message = 'you already sent that user a friend request, leave him alone'
        
class AlreadyDeletedRequested(RelationError):
    message = 'you already deleted that request'
        
class AlreadyFriend(RelationError):
    message = 'you cannot accept a request twice'
        
class NotAFriendCanNotBeUnfriend(RelationError):
    message = 'you cannot unfriend someone who is not your friend, but you can block them'
    
class NoRequestNoFriendship(RelationError):
    message = 'you cannot become friends with someone who has not sent a friend request'
