import grpc
from grpc._channel import _InactiveRpcError

from seekers import DecideCallable
from seekers.grpc import remote_control_types as types
from seekers.grpc.converters import *
import seekers

import logging
import sys

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, style="{", format="[{levelname}] {message}")


class GrpcSeekersClientError(Exception): ...


class SessionTokenInvalidError(GrpcSeekersClientError): ...


class GameFullError(GrpcSeekersClientError): ...


class ServerUnavailableError(GrpcSeekersClientError): ...


class GrpcSeekersRawClient:
    def __init__(self, address: str = "localhost:7777"):
        self.channel = grpc.insecure_channel(address)
        self.stub = pb2_grpc.SeekersStub(self.channel)

    def join_session(self, ai_name: str) -> str:
        """Try to join the game and return our player_id."""
        try:
            return self.stub.JoinSession(SessionRequest(token=ai_name)).id
        except _InactiveRpcError as e:
            if e.code() == grpc.StatusCode.UNAUTHENTICATED:
                raise SessionTokenInvalidError(f"Session token {ai_name=} is invalid. It can't be empty.") from e
            elif e.code() == grpc.StatusCode.RESOURCE_EXHAUSTED:
                raise GameFullError("The game is full.") from e
            elif e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServerUnavailableError(
                    f"The server is unavailable. Is it running already?"
                ) from e
            raise

    def server_properties(self) -> dict[str, str]:
        return self.stub.PropertiesInfo(PropertiesRequest()).entries

    def entities(self) -> types._EntityReply:
        return self.stub.EntityStatus(EntityRequest())

    def players_info(self) -> types._PlayerReply:
        return self.stub.PlayerStatus(PlayerRequest())

    def send_command(self, player_id: str, id_: str, target: Vector, magnet: float) -> None:
        self.stub.CommandUnit(CommandRequest(token=player_id, id=id_, target=target, magnet=magnet))

    def __del__(self):
        self.channel.close()


class GrpcSeekersClient:
    def __init__(self, ai_name: str, decide_function: DecideCallable, address: str = "localhost:7777"):
        self.decide_function = decide_function

        self._logger = logging.getLogger(self.__class__.__name__)

        self.client = GrpcSeekersRawClient(address)

        self._logger.debug(f"Joining session as {ai_name!r}...")
        self.player_id = self.client.join_session(ai_name)
        self.ai_name = ai_name

        self._logger.debug(f"Joined session as {self.player_id=}")

        self._logger.debug(f"Properties: {self.client.server_properties()!r}")

    def mainloop(self):
        while 1:
            entity_reply = self.client.entities()
            player_reply = self.client.players_info()
            props = self.client.server_properties()

            all_seekers, goals = entity_reply.seekers, entity_reply.goals
            camps, players = player_reply.camps, player_reply.players

            try:
                own_player = players[self.player_id]
            except IndexError as e:
                raise GrpcSeekersClientError("Invalid Response: Own player_id not in PlayerReply.players")

            # self._logger.debug(
            #     f"Own seekers: {len(own_seekers)}, other seekers: {len(other_seekers)}, Teams: {len(players)}")

            converted_seekers = {seeker_id: convert_seeker(seeker, props) for seeker_id, seeker in all_seekers.items()}

            converted_players = {player_id: convert_player(player, converted_seekers) for player_id, player in
                                 players.items()}

            converted_camps = {player_id: convert_camp(camp, converted_players) for player_id, camp in camps.items()}

            converted_goals = [convert_goal(goal, props) for goal in goals.values()]

            converted_my_seekers = [converted_seekers[seeker_id] for seeker_id in own_player.seeker_ids]
            converted_other_seekers = [converted_seekers[seeker_id] for seeker_id in all_seekers if
                                       seeker_id not in own_player.seeker_ids]

            converted_other_players = [converted_players[player_id] for player_id in players if
                                       player_id != self.player_id]

            try:
                converted_own_camp = converted_camps[own_player.camp_id]
            except IndexError as e:
                raise GrpcSeekersClientError("Invalid Response: Own camp not in PlayerReply.camps") from e

            converted_world = seekers.World(float(props["map.width"]), float(props["map.height"]))

            new_seekers = self.decide_function(
                converted_my_seekers,
                converted_other_seekers,
                list(converted_seekers.values()),
                converted_goals,
                converted_other_players,
                converted_own_camp,
                list(converted_camps.values()),
                converted_world
            )

            self.send_updates(new_seekers)

    def send_updates(self, new_seekers: list[seekers.Seeker]):
        self._logger.debug(f"Sending {len(new_seekers)} commands")

        for seeker in new_seekers:
            try:
                self.client.send_command(self.ai_name, seeker.id, convert_vector_back(seeker.target), seeker.magnet.strength)
            except _InactiveRpcError as e:
                if e.code() == grpc.StatusCode.CANCELLED:
                    self._logger.warning("Received CANCELLED")
                else:
                    raise

    print(f"Game Over.")


if __name__ == "__main__":
    main()
