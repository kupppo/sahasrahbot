import datetime

import tortoise.exceptions
from quart import (Blueprint, abort, jsonify, redirect,
                   render_template, request, url_for)
from quart_discord import requires_authorization

from alttprbot import models
from alttprbot_api import auth

from ..api import discord

asynctournament_blueprint = Blueprint('async', __name__)


@asynctournament_blueprint.route('/api/tournaments', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournaments():
    filter_args = {}
    if request.args.get('active'):
        filter_args['active'] = request.args.get('active') == 'true'

    result = await models.AsyncTournament.filter(**filter_args)
    return jsonify([asynctournament_to_dict(t) for t in result])


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournament_by_id(tournament_id):
    result = await models.AsyncTournament.get_or_none(id=tournament_id)
    if result is None:
        return jsonify({'error': 'Tournament not found.'})

    return jsonify(asynctournament_to_dict(result))


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/races', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournament_races(tournament_id):
    filter_args = {}
    if request.args.get('id'):
        filter_args['id'] = request.args.get('id')
    if request.args.get('discord_user_id'):
        filter_args['discord_user_id'] = request.args.get('discord_user_id')
    if request.args.get('permalink_id'):
        filter_args['permalink_id'] = request.args.get('permalink_id')
    if request.args.get('pool_id'):
        filter_args['permalink__pool_id'] = request.args.get('pool_id')
    if request.args.get('pool_name'):
        filter_args['permalink__pool__name'] = request.args.get('pool_name')
    if request.args.get('status'):
        filter_args['status'] = request.args.get('status')

    result = await models.AsyncTournamentRace.filter(tournament_id=tournament_id, **filter_args).prefetch_related('tournament', 'user', 'permalink', 'permalink__pool')
    if result is None:
        return jsonify({'error': 'Tournament not found.'})

    # figure out how to also return the permalink and tournament data
    return jsonify([asynctournamentrace_to_dict(r) for r in result])


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/pools', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournament_pools(tournament_id):
    result = await models.AsyncTournamentPermalinkPool.filter(tournament_id=tournament_id).prefetch_related('tournament')
    if result is None:
        return jsonify({'error': 'No pools found.'})

    return jsonify([asynctournamentpermalinkpool_to_dict(r) for r in result])


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/pools/<int:pool_id>', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournament_pool(tournament_id, pool_id):
    result = await models.AsyncTournamentPermalinkPool.get_or_none(tournament_id=tournament_id, id=pool_id)
    if result is None:
        return jsonify({'error': 'Pool not found.'})

    return jsonify(asynctournamentpermalinkpool_to_dict(result))


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/permalinks', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournament_permalinks(tournament_id):
    filter_args = {}
    if request.args.get('id'):
        filter_args['id'] = request.args.get('id')
    if request.args.get('permalink'):
        filter_args['permalink'] = request.args.get('permalink')
    if request.args.get('pool_id'):
        filter_args['pool_id'] = request.args.get('pool_id')

    result = await models.AsyncTournamentPermalink.filter(pool__tournament_id=tournament_id, **filter_args).prefetch_related('pool')
    if result is None:
        return jsonify({'error': 'No permalinks found.'})

    return jsonify([asynctournamentpermalink_to_dict(r) for r in result])


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/permalinks/<int:permalink_id>', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournament_permalink(tournament_id, permalink_id):
    result = await models.AsyncTournamentPermalink.get_or_none(pool__tournament_id=tournament_id, id=permalink_id)
    if result is None:
        return jsonify({'error': 'Permalink not found.'})

    return jsonify(asynctournamentpermalink_to_dict(result))


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/whitelist', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournament_whitelist(tournament_id):
    result = await models.AsyncTournamentWhitelist.filter(tournament_id=tournament_id).prefetch_related('tournament')
    if result is None:
        return jsonify({'error': 'Tournament not found.'})

    return jsonify([asynctournamentwhitelist_to_dict(r) for r in result])


@asynctournament_blueprint.route('/races/<int:tournament_id>', methods=['GET'])
@requires_authorization
async def async_tournament_queue(tournament_id: int):
    discord_user = await discord.fetch_user()
    user = await models.Users.get_or_none(discord_user_id=discord_user.id)

    request_filter = {}

    if not (status := request.args.get('status', 'finished')) == 'all':
        request_filter['status'] = status

    if not (reviewer := request.args.get('reviewed', 'all')) == 'all':
        if reviewer == 'unreviewed':
            request_filter['reviewed_by'] = None
        elif reviewer == 'me':
            request_filter['reviewed_by'] = user
        else:
            try:
                request_filter['reviewed_by_id'] = int(reviewer)
            except ValueError:
                pass

    if not (review_status := request.args.get('review_status', 'pending')) == 'all':
        request_filter['review_status'] = review_status

    if not (live := request.args.get('live', 'false')) == 'all':
        request_filter['thread_id__isnull'] = live == 'true'

    tournament = await models.AsyncTournament.get(id=tournament_id)

    authorized = await tournament.permissions.filter(user=user, role__in=['admin', 'mod'])
    if not authorized:
        return abort(403, "You are not authorized to view this tournament.")

    races = await tournament.races.filter(reattempted=False, **request_filter).prefetch_related('user', 'reviewed_by', 'permalink', 'permalink__pool')

    return await render_template('asynctournament_race_list.html', logged_in=True, user=discord_user, tournament=tournament, races=races)


@asynctournament_blueprint.route('/races/<int:tournament_id>/review/<int:race_id>', methods=['GET'])
@requires_authorization
async def async_tournament_review(tournament_id: int, race_id: int):
    discord_user = await discord.fetch_user()
    user = await models.Users.get_or_none(discord_user_id=discord_user.id)

    tournament = await models.AsyncTournament.get(id=tournament_id)

    authorized = await tournament.permissions.filter(user=user, role__in=['admin', 'mod'])
    if not authorized:
        return abort(403, "You are not authorized to view this tournament.")

    race = await models.AsyncTournamentRace.get_or_none(id=race_id, tournament=tournament)
    if race is None:
        abort(404, "Race not found.")

    if race.status != 'finished':
        abort(403, "This race cannot be reviewed yet.")

    if race.reattempted:
        abort(403, "This race was marked as reattempted and cannot be reviewed.")

    await race.fetch_related('user', 'reviewed_by', 'permalink', 'permalink__pool')

    if race.user == user:
        abort(403, "You are not authorized to review your own tournament run.")

    if race.reviewed_by is None:
        race.reviewed_by = user
        await race.save()

    return await render_template('asynctournament_race_view.html', logged_in=True, user=discord_user, tournament=tournament, race=race, already_claimed=race.reviewed_by != user)


@asynctournament_blueprint.route('/races/<int:tournament_id>/review/<int:race_id>', methods=['POST'])
@requires_authorization
async def async_tournament_review_submit(tournament_id: int, race_id: int):
    discord_user = await discord.fetch_user()
    user = await models.Users.get_or_none(discord_user_id=discord_user.id)

    tournament = await models.AsyncTournament.get(id=tournament_id)

    authorized = await tournament.permissions.filter(user=user, role__in=['admin', 'mod'])
    if not authorized:
        return abort(403, "You are not authorized to view this tournament.")

    race = await models.AsyncTournamentRace.get_or_none(id=race_id, tournament=tournament)
    if race is None:
        abort(404, "Race not found.")

    if race.status != 'finished':
        abort(403, "This race cannot be reviewed yet.")

    if race.reattempted:
        abort(403, "This race was marked as reattempted and cannot be reviewed.")

    if race.user == user:
        abort(403, "You are not authorized to review your own tournament run.")

    payload = await request.form

    race.review_status = payload.get('review_status', 'pending')
    race.reviewer_notes = payload.get('reviewer_notes', None)
    race.reviewed_at = datetime.datetime.now()
    race.reviewed_by = user

    await race.save()

    return redirect(url_for("async.async_tournament_queue", tournament_id=tournament_id))


def asynctournament_to_dict(asynctournament: models.AsyncTournament):
    try:
        return {
            'id': asynctournament.id,
            'name': asynctournament.name,
            'active': asynctournament.active,
            'created': asynctournament.created,
            'updated': asynctournament.updated,
            'guild_id': asynctournament.guild_id,
            'channel_id': asynctournament.channel_id,
            'owner_id': asynctournament.owner_id,
            'allowed_reattempts': asynctournament.allowed_reattempts,
        }
    except AttributeError:
        return None
    except tortoise.exceptions.NoValuesFetched:
        return None


def asynctournamentwhitelist_to_dict(asynctournamentwhitelist: models.AsyncTournamentWhitelist):
    try:
        return {
            'id': asynctournamentwhitelist.id,
            'tournament': asynctournament_to_dict(asynctournamentwhitelist.tournament),
            'user': users_to_dict(asynctournamentwhitelist.user),
        }
    except AttributeError:
        return None
    except tortoise.exceptions.NoValuesFetched:
        return None


def asynctournamentpermalink_to_dict(asynctournamentpermalink: models.AsyncTournamentPermalink):
    try:
        return {
            'id': asynctournamentpermalink.id,
            'permalink': asynctournamentpermalink.url,
            'pool': asynctournamentpermalinkpool_to_dict(asynctournamentpermalink.pool),
            'live_race': asynctournamentpermalink.live_race
        }
    except AttributeError:
        return None
    except tortoise.exceptions.NoValuesFetched:
        return None


def asynctournamentpermalinkpool_to_dict(asynctournamentpermalinkpool: models.AsyncTournamentPermalinkPool):
    try:
        return {
            'id': asynctournamentpermalinkpool.id,
            'tournament': asynctournament_to_dict(asynctournamentpermalinkpool.tournament),
            'name': asynctournamentpermalinkpool.name,
        }
    except AttributeError:
        return None
    except tortoise.exceptions.NoValuesFetched:
        return None


def asynctournamentrace_to_dict(asynctournamentrace: models.AsyncTournamentRace):
    try:
        return {
            'id': asynctournamentrace.id,
            'tournament': asynctournament_to_dict(asynctournamentrace.tournament),
            'permalink': asynctournamentpermalink_to_dict(asynctournamentrace.permalink),
            'user': users_to_dict(asynctournamentrace.user),
            'thread_id': asynctournamentrace.thread_id,
            'thread_open_time': asynctournamentrace.thread_open_time,
            'thread_timeout_time': asynctournamentrace.thread_timeout_time,
            'start_time': asynctournamentrace.start_time,
            'end_time': asynctournamentrace.end_time,
            'created': asynctournamentrace.created,
            'updated': asynctournamentrace.updated,
            'status': asynctournamentrace.status,
            'live_race': asynctournamentrace.live_race, # TODO: translate to dictionary
            'reattempted': asynctournamentrace.reattempted,
            'runner_notes': asynctournamentrace.runner_notes,
            'runner_vod_url': asynctournamentrace.runner_vod_url,
            'review_status': asynctournamentrace.review_status,
            'reviewed_by': users_to_dict(asynctournamentrace.reviewed_by),
            'reviewed_at': asynctournamentrace.reviewed_at,
            'reviewer_notes': asynctournamentrace.reviewer_notes,
        }
    except AttributeError:
        return None
    except tortoise.exceptions.NoValuesFetched:
        return None


def users_to_dict(user: models.Users):
    try:
        return {
            'id': user.id,
            'discord_user_id': user.discord_user_id,
            'display_name': user.display_name,
            'rtgg_id': user.rtgg_id,
        }
    except AttributeError:
        return None
    except tortoise.exceptions.NoValuesFetched:
        return None
