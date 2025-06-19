import graphene
from graphene_django import DjangoObjectType
from users.schema import UserType
from graphql import GraphQLError
from django.db.models import Q


from .models import Comment, Songs, Vote


class SongType(DjangoObjectType):
    total_count = graphene.Int()
    comments = graphene.List(lambda: CommentType)
    most_voted_rating = graphene.Int()

    class Meta:
        model = Songs

    def resolve_total_count(self, info):
        return self.votes.count()
    
    def resolve_comments(self, info):
        return self.comments.all()
    
    def resolve_most_voted_rating(self, info):
        from django.db.models import Count

        vote_counts = (
            self.votes.values('rating')
            .annotate(count=Count('rating'))
            .order_by('-count', '-rating')  # desempate por rating mayor
        )
        return vote_counts[0]['rating'] if vote_counts else None



class VoteType(DjangoObjectType):
    class Meta:
        model = Vote

class CommentType(DjangoObjectType):
    class Meta:
        model = Comment

class Query(graphene.ObjectType):
    Songs = graphene.List(SongType)

    def resolve_Songs(self, info, **kwargs):
        return Songs.objects.all()
    


class Query(graphene.ObjectType):
    songs = graphene.List(
        SongType,
        search=graphene.String(),
        first=graphene.Int(),
        skip=graphene.Int(),
    )
    votes = graphene.List(VoteType)
    comments = graphene.List(CommentType, song_id=graphene.Int())

    def resolve_songs(self, info, search=None, first=None, skip=None, **kwargs):
        qs = Songs.objects.all()
        if search:
            filter = Q(url__icontains=search) | Q(descripcion__icontains=search)
            qs = qs.filter(filter)
        if skip:
            qs = qs[skip:]
        if first:
            qs = qs[:first]
        return qs

    def resolve_votes(self, info, **kwargs):
        return Vote.objects.all()
    
    def resolve_comments(self, info, song_id=None, **kwargs):
        if song_id:
            return Comment.objects.filter(song__id=song_id)
        return Comment.objects.all()
    
class DeleteSong(graphene.Mutation):
    ok = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        song_id = graphene.Int(required=True)

    def mutate(self, info, song_id):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError("You must be logged in to delete a song.")

        try:
            song = Songs.objects.get(id=song_id)
        except Songs.DoesNotExist:
            raise GraphQLError("Song not found.")

        if song.posted_by != user:
            raise GraphQLError("You are not authorized to delete this song.")

        song.delete()
        return DeleteSong(ok=True, message="Song deleted successfully.")
    
class CreateSong(graphene.Mutation):
    id = graphene.Int()
    url = graphene.String()
    titulo = graphene.String()
    descripcion = graphene.String()
    posted_by = graphene.Field(UserType)

    class Arguments:
        url = graphene.String(required=True)
        titulo = graphene.String(required=False)
        descripcion = graphene.String(required=False)

    def mutate(self, info, url, titulo=None, descripcion=None):
        user = info.context.user or None

        song = Songs(
            url=url,
            titulo=titulo or "",
            descripcion=descripcion or "",
            posted_by=user,
        )
        song.save()

        return CreateSong(
            id=song.id,
            url=song.url,
            titulo=song.titulo,
            descripcion=song.descripcion,
            posted_by=song.posted_by,
        )


class CreateComment(graphene.Mutation):
    comment = graphene.Field(CommentType)

    class Arguments:
        song_id = graphene.Int(required=True)
        text = graphene.String(required=True)

    def mutate(self, info, song_id, text):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError("You must be logged in to comment!")

        song = Songs.objects.filter(id=song_id).first()
        if not song:
            raise GraphQLError("Invalid Song!")

        comment = Comment.objects.create(
            user=user,
            song=song,
            text=text
        )

        return CreateComment(comment=comment)



class CreateVote(graphene.Mutation):
    user = graphene.Field(UserType)
    song = graphene.Field(SongType) 

    class Arguments:
        song_id = graphene.Int(required=True)
        rating = graphene.Int(required=True)

    def mutate(self, info, song_id, rating):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError('You must be logged in to vote!')

        if rating < 1 or rating > 5:
            raise GraphQLError('Rating must be between 1 and 5.')

        song = Songs.objects.filter(id=song_id).first()
        if not song:
            raise GraphQLError('Invalid Song!')

        # Update vote if already exists
        vote, created = Vote.objects.update_or_create(
            user=user,
            songs=song,
            defaults={'rating': rating}
        )

        return CreateVote(user=user, song=song)


class Mutation(graphene.ObjectType):
    create_song = CreateSong.Field()
    create_vote = CreateVote.Field()
    create_comment = CreateComment.Field()
    delete_song = DeleteSong.Field()