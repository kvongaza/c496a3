"""
Module for playing games of Go using GoTextProtocol

This code is based off of the gtp module in the Deep-Go project
by Isaac Henrion and Aamos Storkey at the University of Edinburgh.
"""
import traceback
import sys
import os
from board_util import GoBoardUtil, BLACK, WHITE, EMPTY, BORDER, FLOODFILL
import gtp_connection
import numpy as np
import re

class GtpConnection(gtp_connection.GtpConnection):

    def __init__(self, go_engine, board, outfile = 'gtp_log', debug_mode = False):
        """
        GTP connection of Go3

        Parameters
        ----------
        go_engine : GoPlayer
            a program that is capable of playing go by reading GTP commands
        komi : float
            komi used for the current game
        board: GoBoard
            SIZExSIZE array representing the current board state
        """
        gtp_connection.GtpConnection.__init__(self, go_engine, board, outfile, debug_mode)
        self.commands["go_safe"] = self.safety_cmd
        self.argmap["go_safe"] = (1, 'Usage: go_safe {w,b}')
        self.commands["timelimit"] = self.timelimit_cmd
        self.argmap["timelimit"] = (1, 'Usage: timelimit INT [1,100]')
        self.commands["solve"] = self.solve_cmd

        # initialize defaults
        self.timelimit = 1

    def safety_cmd(self, args):
        try:
            color= GoBoardUtil.color_to_int(args[0].lower())
            safety_list = self.board.find_safety(color)
            safety_points = []
            for point in safety_list:
                x,y = self.board._point_to_coord(point)
                safety_points.append(GoBoardUtil.format_point((x,y)))
            self.respond(safety_points)
        except Exception as e:
            self.respond('Error: {}'.format(str(e)))

    # sets the maximum time to use for all following genmove or solve commands
    def timelimit_cmd(self, args):
        try:
            args_0 = int(args[0])
            if (1 > args_0 or args_0 > 100):
                raise
        except:
            print(self.argmap["timelimit"][1])
            return

        self.timelimit = args_0
        self.respond()
        return

    def policy_moves_cmd(self, args):
        if self.board.last_move is not None:    
            if self.atari_cap():
                return
            if self.atari_def():
                return
        policy_moves, type_of_move = GoBoardUtil.generate_all_policy_moves(self.board, self.go_engine.use_pattern, self.go_engine.check_selfatari)
        if len(policy_moves) == 0:
            self.respond('Pass')
        else:
            response = type_of_move + ' ' + GoBoardUtil.sorted_point_string(policy_moves,  self.board.NS)
            self.respond(response)

    # compute the winner of the current position, assuming perfect play by both,
    # within the current time limit.
    def solve_cmd(self, args):
        self.respond(self.go_engine.solve(self.board, self))

    def atari_cap(self):
        last_move = self.board.last_move
        opp = GoBoardUtil.opponent(self.board.current_player)
        if self.board._liberty(last_move, opp) == 1:
            cap = self.board._single_liberty(last_move, opp)
            if GoBoardUtil.filter(self.board, cap, self.board.current_player, True):
                return False
            board = self.board.copy()
            legal = board.move(cap, self.board.current_player)
            if legal:
                self.respond('AtariCapture ' + GoBoardUtil.sorted_point_string([cap], self.board.NS))
                return True
        return False

    def atari_def(self):
        player = self.board.current_player
        last_move = self.board.last_move
        if last_move is None:
            return False
        S, _, _ = self.board.find_S_and_E(player)
        moves = []
        for stone in S:
            if self.board._liberty(stone, player) == 1:
                defense_p = self.board._single_liberty(stone, player)
                board = self.board.copy()
                board.move(defense_p, player)
                if board._liberty(defense_p, player) > 1:
                    moves.append(defense_p)
        moves = GoBoardUtil.filter_moves(self.board, moves, True)
        if len(moves) < 1:
            return False
        self.respond('AtariDefense ' + GoBoardUtil.sorted_point_string(moves, self.board.NS))
        return True
