
import sys
import argparse
import re
import binascii
import struct
from hashlib import sha256

fileTypes = [
    ['.mpg', b'\x00\x00\x01\xB3\x00', b'\x00\x00\x00\x01\xB7'],
    ['.pdf',  b'\x25\x50\x44\x46', b'\x0A\x25\x25\x45\x4F\x46\x0A'],
    ['.pdf',  b'\x25\x50\x44\x46', b'\x0D\x0A\x25\x25\x45\x4F\x46\x0D\x0A'],
    ['.pdf',  b'\x25\x50\x44\x46', b'\x0A\x25\x25\x45\x4F\x46'],
    ['.pdf',  b'\x25\x50\x44\x46', b'\x0D\x25\x25\x45\x4F\x46\x0D'],
    ['.bmp', b'\x42\x4D....\x00\x00\x00\x00', None],
    ['.gif', b'\x47\x49\x46\x38\x37\x61', b'\x00\x00\x3B'],
    ['.gif', b'\x47\x49\x46\x38\x39\x61', b'\x00\x00\x3B'],
    ['.jpg', b'\xFF\xD8\xFF\xE0', b'\xFF\xD9'],
    ['.jpg', b'\xFF\xD8\xFF\xE1', b'\xFF\xD9'],
    ['.jpg', b'\xFF\xD8\xFF\xE2', b'\xFF\xD9'],
    ['.jpg', b'\xFF\xD8\xFF\xE8', b'\xFF\xD9'],
    ['.jpg', b'\xFF\xD8\xFF\xDB', b'\xFF\xD9'],
    ['.docx', b'\x50\x4B\x03\x04\x14\x00\x06\x00', b'\x50\x4B\x05\x06'],
    ['.avi', b'\x52\x49\x46\x46....\x41\x56\x49\x20\x4C\x49\x53\x54', None],
    ['.png', b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A', b'\x49\x45\x4E\x44\xAE\x42\x60\x82']
]

def main():

    # Command line args and parser
    #
    # Source: https://docs.python.org/3/howto/argparse.html

    parser = argparse.ArgumentParser()
    parser.add_argument("diskImage")
    args = parser.parse_args()
    if args is None:
        sys.exit()

    fileName = args.diskImage

    # These are lists to keep track of which headers and footers are already carved.
    # Will be used with the flags to make sure we do not carve multiple times.
    headerList = []
    footerList = []

    # File counter
    fileCount = 1

    # Opening the file from command line
    file = open(fileName, 'rb')
    b = file.read()
    file.close()

    # Flags used for carving valid files. False is valid.
    headerFlag = False
    footerFlag = False
    pdfFlag = False

    # Goes through each file in the list.

    for f in fileTypes:
        # Using the fileTypes list we can use the regex import to compile patterns for the headers

        regHeader = re.compile(f[1])

        # Iterates through the compiled list of headers
        #
        # Source: https://docs.python.org/2/library/re.html

        for matchHeader in regHeader.finditer(b):

            # The first match indicates the offset start

            offset = matchHeader.start()
            headerFlag = False

            # Skip if already carved
            if offset in headerList:
                headerFlag = True

            # Reads file from this offset
            start = b[offset:]

            # Used to find next offset to properly carve .pdf
            nextOffset = 0

            if f[0] == '.pdf' and headerFlag is False:
                for match in regHeader.finditer(b[offset + 1:]):
                    nextOffset = match.start() + offset
                    break

            # Footers only need to be found is header is good

            if headerFlag is False:
                if f[2] is not None:
                    # Using the fileTypes list we can use the regex import to compile patterns for the footers
                    regFooter = re.compile(f[2])

                    for matchFooter in regFooter.finditer(start):
                        
                        # End of the footer match
                        end = matchFooter.end()
                        end += offset

                        pdfFlag = False

                        # Next footer offset
                        nextEnd = 0

                        #
                        # .pdf
                        #
                        # .pdf's can have multiple footers so it's important to check for the correct last footer
                        # This can be done by looking for another header after the last detected footer.
                        # If there is no other header then the last detected footer will be used.

                        if f[0] == '.pdf':

                            for match in regFooter.finditer(b[end:]):
                                nextEnd = match.start() + end
                                break

                            if nextOffset != 0:

                                if end > nextOffset:
                                    pdfFlag = True
                                    break

                                elif nextEnd != 0:
                                    if nextEnd > nextOffset:
                                        break
                        
                        # DOCX has extra 18 bytes after footer
                        elif f[0] == '.docx':
                            end += 18
                            break
                        else:
                            break
                
                else:

                    #
                    # BMP
                    # 
                    # File size is located 2 bytes from start

                    if f[0] == '.bmp':
                        header = 2

                    #
                    # AVI
                    # 
                    # File size is located 4 bytes from start

                    elif f[0] == '.avi':
                        header = 4

                    sizeStart = offset + header

                    # Formatting the hex and converting it to a byte. Then converting to a long
                    size = str(hex(b[sizeStart])[2:].zfill(2)) + str(hex(b[sizeStart+1])[2:]).zfill(2) + str(hex(b[sizeStart+2])[2:].zfill(2)) + str(hex(b[sizeStart+3])[2:].zfill(2))
                    sizeB = binascii.unhexlify(size)

                    longSize = struct.unpack('<l', sizeB)
                    end = offset + longSize[0]

                    if f[0] == '.avi':
                        end += 8
            
            # Checks to see if the footer offset is already listed. If so, skip.
            footerFlag = False
            if end in footerList:
                footerFlag = True

            # If all offsets are valid then the file will be carved.
            if not (headerFlag or footerFlag or pdfFlag):

                # Add the offsets to their respective lists
                headerList.append(offset)
                footerList.append(end)

                # Data from header offset to footer offset will be written to a new file
                newFile = b[offset:end]
                newFileName = 'file' + str(fileCount) + f[0]
                fileOutput = open(newFileName, "wb")
                fileOutput.write(newFile)
                fileOutput.close()

                # Get hash for the new file
                fileHash = sha256(newFileName)

                # File counter is then incremented
                fileCount += 1

                # All the new file input is then printed
                print("\nFile Name: " + newFileName)
                print("Starting Offset: " + hex(offset))
                print("End Offset: " + hex(end))
                print("SHA-256 Hash: " + fileHash)

if __name__ == '__main__':
    main()